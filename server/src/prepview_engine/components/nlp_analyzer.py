
import whisper
import librosa
import numpy as np
import nltk
import re
import spacy
from collections import Counter
from pathlib import Path
from prepview_engine.utils.common import logger
from prepview_engine.config.configuration import NLPConfig
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import sent_tokenize, word_tokenize

# NLTK Downloads (Safe check)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt')
    nltk.download('punkt_tab')

class NLPAnalyzerComponent:
    # --- SHARED MODELS (Optimized for speed) ---
    _models_loaded = False
    _whisper_model = None
    _nlp_spacy = None
    _embedder = None

    def __init__(self, config: NLPConfig):
        """
        Initializes NLP models and configuration.
        Audio path is now passed in run() method.
        """
        self.config = config
        
        # Load models ONLY if they haven't been loaded yet (Singleton Pattern)
        if not NLPAnalyzerComponent._models_loaded:
            logger.info("⏳ Loading NLP Models (Whisper, Spacy, BERT)... This happens only once.")
            
            # 1. Load Whisper
            NLPAnalyzerComponent._whisper_model = whisper.load_model(self.config.whisper_model)
            
            # 2. Load Spacy
            try:
                NLPAnalyzerComponent._nlp_spacy = spacy.load(self.config.spacy_model)
            except OSError:
                logger.warning(f"Spacy model '{self.config.spacy_model}' not found. Downloading...")
                from spacy.cli import download
                download(self.config.spacy_model)
                NLPAnalyzerComponent._nlp_spacy = spacy.load(self.config.spacy_model)

            # 3. Load Sentence Transformer
            NLPAnalyzerComponent._embedder = SentenceTransformer(self.config.transformer_model)
            
            NLPAnalyzerComponent._models_loaded = True
            logger.info("✅ NLP Models Loaded Successfully.")
        
        # Assign shared models to instance for easy access
        self.whisper_model = NLPAnalyzerComponent._whisper_model
        self.nlp_spacy = NLPAnalyzerComponent._nlp_spacy
        self.embedder = NLPAnalyzerComponent._embedder
        
        # Instance variable for current audio processing
        self.audio_path = None
        
        logger.info("NLPAnalyzerComponent Initialized.")

    # ==========================================================
    # 🎤 HELPER: LOAD & TRANSCRIBE
    # ==========================================================
    def _load_audio(self):
        """Loads audio using Librosa."""
        y, sr = librosa.load(self.audio_path, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        return y, sr, duration

    def _transcribe_audio(self):
        """Transcribes audio using Whisper."""
        return self.whisper_model.transcribe(
            self.audio_path,
            language=self.config.whisper_language,
            word_timestamps=True
        )

    # ==========================================================
    # 📊 HELPER: METRICS EXTRACTION
    # ==========================================================
    def _temporal_hesitation_metrics(self, words):
        gaps = []
        for i in range(len(words) - 1):
            gap = words[i+1]["start"] - words[i]["end"]
            if gap > 0:
                gaps.append(gap)

        long_pauses = [g for g in gaps if g > self.config.pause_threshold]

        pause_density = len(long_pauses) / max(len(words), 1)
        pause_variance = np.std(gaps) if gaps else 0.0

        return {
            "pause_density": round(pause_density, 3),
            "pause_variance": round(pause_variance, 3)
        }

    def _extract_speech_metrics(self, transcript, duration):
        words = []
        for seg in transcript["segments"]:
            words.extend(seg.get("words", []))

        if len(words) < 2:
            return {}, words

        # --- Speech rate ---
        total_words = len(words)
        speech_rate_wpm = total_words / (duration / 60)

        # --- Pause calculations ---
        pauses = []
        for i in range(len(words) - 1):
            gap = words[i+1]["start"] - words[i]["end"]
            if gap > 0:
                pauses.append(gap)

        long_pauses = [p for p in pauses if p > self.config.pause_threshold]

        total_pause_time = sum(pauses)
        pause_ratio = total_pause_time / duration
        avg_pause_duration = np.mean(long_pauses) if long_pauses else 0.0
        silence_to_speech_ratio = total_pause_time / max(duration - total_pause_time, 1e-5)

        # --- Behavioral filler replacement ---
        filler_rate = len(long_pauses) / max(total_words, 1)

        # --- Rhythm stability ---
        inter_word_intervals = [
            words[i+1]["start"] - words[i]["end"]
            for i in range(len(words) - 1)
        ]
        rhythm_stability = np.std(inter_word_intervals) if inter_word_intervals else 0.0

        # --- Pause dynamics ---
        hesitation = self._temporal_hesitation_metrics(words)

        return {
            "speech_rate_wpm": round(speech_rate_wpm, 2),
            "pause_ratio": round(pause_ratio, 3),
            "avg_pause_duration": round(avg_pause_duration, 2),
            "silence_to_speech_ratio": round(silence_to_speech_ratio, 2),
            "filler_rate": round(filler_rate, 3),
            "rhythm_stability": round(rhythm_stability, 3),
            "pause_density": hesitation["pause_density"],
            "pause_variance": hesitation["pause_variance"]
        }, words

    def _syntactic_uncertainty(self, text):
        doc = self.nlp_spacy(text)

        aux_verbs = 0
        subordinate_clauses = 0

        for token in doc:
            if token.dep_ == "aux":
                aux_verbs += 1
            if token.dep_ in {"mark", "advcl", "ccomp"}:
                subordinate_clauses += 1

        total_tokens = len(doc)

        return {
            "aux_verb_ratio": round(aux_verbs / max(total_tokens, 1), 3),
            "subordinate_clause_ratio": round(subordinate_clauses / max(total_tokens, 1), 3)
        }

    def _semantic_instability(self, sentences):
        if len(sentences) < 2:
            return 0.0

        embeddings = self.embedder.encode(sentences)
        sims = []

        for i in range(len(embeddings) - 1):
            sim = cosine_similarity(
                [embeddings[i]], [embeddings[i+1]]
            )[0][0]
            sims.append(sim)

        return round(1 - np.mean(sims), 3)

    def _extract_linguistic_metrics(self, text):
        sentences = sent_tokenize(text)
        words = word_tokenize(text.lower())

        total_words = len(words)
        unique_words = len(set(words))

        lexical_richness = unique_words / max(total_words, 1)

        sentence_lengths = [len(word_tokenize(s)) for s in sentences]
        sentence_length_std = np.std(sentence_lengths) if sentence_lengths else 0.0

        word_counts = Counter(words)
        repeated_words = sum(c for c in word_counts.values() if c > 1)
        repetition_ratio = repeated_words / max(total_words, 1)

        syntactic = self._syntactic_uncertainty(text)
        semantic_drift = self._semantic_instability(sentences)

        return {
            "lexical_richness": round(lexical_richness, 3),
            "sentence_length_std": round(sentence_length_std, 2),
            "repetition_ratio": round(repetition_ratio, 3),
            "syntactic_uncertainty": syntactic,
            "semantic_instability": semantic_drift
        }

    # ==========================================================
    # 🏆 SCORING SYSTEM (Config Driven)
    # ==========================================================
    def _compute_phase1_quality_score(self, speech, linguistic):
        score = 100.0
        cfg = self.config # Short alias

        # 1. Speech Fluency
        wpm = speech.get("speech_rate_wpm", 0)
        rhythm = speech.get("rhythm_stability", 0)

        if wpm < cfg.wpm_min or wpm > cfg.wpm_max:
            score -= cfg.penalty_wpm_high
        elif wpm < cfg.wpm_strict_min or wpm > cfg.wpm_strict_max:
            score -= cfg.penalty_wpm_med

        if rhythm > cfg.rhythm_stability_high:
            score -= cfg.penalty_rhythm_high
        elif rhythm > cfg.rhythm_stability_med:
            score -= cfg.penalty_rhythm_med

        # 2. Pause & Hesitation
        if speech.get("pause_ratio", 0) > cfg.pause_ratio_high:
            score -= cfg.penalty_pause_ratio_high
        elif speech.get("pause_ratio", 0) > cfg.pause_ratio_med:
            score -= cfg.penalty_pause_ratio_med

        if speech.get("avg_pause_duration", 0) > cfg.avg_pause_high:
            score -= cfg.penalty_avg_pause_high
        elif speech.get("avg_pause_duration", 0) > cfg.avg_pause_med:
            score -= cfg.penalty_avg_pause_med

        if speech.get("filler_rate", 0) > cfg.filler_rate_high:
            score -= cfg.penalty_filler_high
        elif speech.get("filler_rate", 0) > cfg.filler_rate_med:
            score -= cfg.penalty_filler_med

        # 3. Linguistic Clarity
        if linguistic.get("lexical_richness", 0) < cfg.lexical_richness_low:
            score -= cfg.penalty_lexical_high
        elif linguistic.get("lexical_richness", 0) < cfg.lexical_richness_med:
            score -= cfg.penalty_lexical_med

        if linguistic.get("repetition_ratio", 0) > cfg.repetition_ratio_high:
            score -= cfg.penalty_repetition_high
        elif linguistic.get("repetition_ratio", 0) > cfg.repetition_ratio_med:
            score -= cfg.penalty_repetition_med

        # 4. Structural Stability
        if linguistic.get("sentence_length_std", 0) > cfg.sentence_length_std_high:
            score -= cfg.penalty_sent_std_high
        elif linguistic.get("sentence_length_std", 0) > cfg.sentence_length_std_med:
            score -= cfg.penalty_sent_std_med

        if linguistic["syntactic_uncertainty"]["aux_verb_ratio"] > cfg.aux_verb_ratio_high:
            score -= cfg.penalty_aux_verb

        if linguistic["semantic_instability"] > cfg.semantic_instability_high:
            score -= cfg.penalty_semantic_high
        elif linguistic["semantic_instability"] > cfg.semantic_instability_med:
            score -= cfg.penalty_semantic_med

        return round(max(0, min(score, 100)), 1)

    # ==========================================================
    # 🚀 MAIN RUNNER
    # ==========================================================
    def run(self, audio_path_str: str):
        """
        Executes Phase-1 linguistic & speech analysis.
        Args:
            audio_path_str (str): Path to the audio file.
        """
        self.audio_path = str(audio_path_str) # Set path for this run
        
        logger.info(f"Running NLP Analysis for: {Path(self.audio_path).name}...")

        try:
            # Load & Transcribe using instance variables
            _, _, duration = self._load_audio()
            transcript = self._transcribe_audio()
            text = transcript.get("text", "").strip()
            
            if not text:
                logger.warning("Transcript is empty. Returning default metrics.")
                return {"error": "Empty transcript", "score": 0}

            # Extract metrics
            speech_metrics, words = self._extract_speech_metrics(transcript, duration)
            linguistic_metrics = self._extract_linguistic_metrics(text)

            # Compute Score
            phase1_score = self._compute_phase1_quality_score(
                speech=speech_metrics,
                linguistic=linguistic_metrics
            )

            logger.info(f"NLP Analysis Complete. Score: {phase1_score}/100")
            
            return {
                "transcript": text,
                "speech_metrics": speech_metrics,
                "linguistic_metrics": linguistic_metrics,
                "phase1_quality_score": phase1_score,
                "prosodic_confidence": 0.0,
                "phase": "phase_1",
                "version": "v1.0"
            }
            
        except Exception as e:
            logger.error(f"NLP Analysis Failed: {e}")
            raise e