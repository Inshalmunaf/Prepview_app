
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


    def prosodic_confidence(self,y, sr, duration):
        """
        Rule-based deterministic prosodic confidence scorer for interview audio.
        
        Parameters:
            y        : np.ndarray  — audio time series (mono)
            sr       : int         — sample rate
            duration : float       — duration in seconds
        
        Returns:
            dict with 'score' (0–100) and per-feature breakdown
        """

        # ------------------------------------------------------------------ #
        #  SAFETY GUARDS                                                       #
        # ------------------------------------------------------------------ #
        if duration < 1.0 or len(y) < sr:
            return {"score": 0, "reason": "Audio too short", "breakdown": {}}

        scores = {}

        # ================================================================== #
        # 1. SPEECH RATE  (words-per-minute proxy via syllable detection)     #
        #    Confident speech: 120–180 WPM  (≈2–3 syllables/sec)             #
        #    Too fast → nervous; too slow → unsure                            #
        # ================================================================== #
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        rms_db = librosa.amplitude_to_db(rms + 1e-6)

        # Rough syllable count: count RMS peaks above threshold
        threshold = np.percentile(rms_db, 40)
        above = (rms_db > threshold).astype(int)
        syllable_crossings = np.sum(np.diff(above) == 1)
        syllable_rate = syllable_crossings / duration  # syllables per second

        if 2.0 <= syllable_rate <= 3.5:
            scores["speech_rate"] = 100
        elif 1.5 <= syllable_rate < 2.0 or 3.5 < syllable_rate <= 4.5:
            scores["speech_rate"] = 70
        elif 1.0 <= syllable_rate < 1.5 or 4.5 < syllable_rate <= 5.5:
            scores["speech_rate"] = 40
        else:
            scores["speech_rate"] = 15

        # ================================================================== #
        # 2. PITCH (F0) STATISTICS                                            #
        #    Confident speakers: moderate pitch, controlled variation         #
        #    Pitch too flat   → monotone / robotic                           #
        #    Pitch too erratic→ nervous / uncertain                          #
        # ================================================================== #
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"),
            sr=sr, hop_length=hop_length
        )
        voiced_f0 = f0[voiced_flag & ~np.isnan(f0)]

        if len(voiced_f0) < 10:
            scores["pitch_variability"] = 30
            scores["pitch_range"] = 30
        else:
            # Pitch variability (CoV = std/mean)
            pitch_cov = np.std(voiced_f0) / (np.mean(voiced_f0) + 1e-6)
            if 0.08 <= pitch_cov <= 0.25:
                scores["pitch_variability"] = 100
            elif 0.05 <= pitch_cov < 0.08 or 0.25 < pitch_cov <= 0.35:
                scores["pitch_variability"] = 65
            elif pitch_cov < 0.05:
                scores["pitch_variability"] = 30   # monotone
            else:
                scores["pitch_variability"] = 40   # overly erratic

            # Pitch range (semitone span)
            p10, p90 = np.percentile(voiced_f0, 10), np.percentile(voiced_f0, 90)
            semitone_range = 12 * np.log2((p90 + 1e-6) / (p10 + 1e-6))
            if 4 <= semitone_range <= 14:
                scores["pitch_range"] = 100
            elif 2 <= semitone_range < 4 or 14 < semitone_range <= 20:
                scores["pitch_range"] = 65
            else:
                scores["pitch_range"] = 30

        # ================================================================== #
        # 3. VOICED RATIO  (speech vs silence proportion)                     #
        #    Too many pauses → hesitant; too few → no breathing room          #
        # ================================================================== #
        voiced_ratio = np.sum(voiced_flag) / (len(voiced_flag) + 1e-6)

        if 0.55 <= voiced_ratio <= 0.85:
            scores["voiced_ratio"] = 100
        elif 0.40 <= voiced_ratio < 0.55 or 0.85 < voiced_ratio <= 0.92:
            scores["voiced_ratio"] = 65
        elif 0.25 <= voiced_ratio < 0.40:
            scores["voiced_ratio"] = 35   # too many pauses
        else:
            scores["voiced_ratio"] = 20

        # ================================================================== #
        # 4. ENERGY CONSISTENCY  (RMS std / mean)                             #
        #    Confident speakers maintain steady volume                         #
        # ================================================================== #
        rms_linear = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        energy_cov = np.std(rms_linear) / (np.mean(rms_linear) + 1e-6)

        if 0.3 <= energy_cov <= 0.9:
            scores["energy_consistency"] = 100
        elif 0.15 <= energy_cov < 0.3 or 0.9 < energy_cov <= 1.2:
            scores["energy_consistency"] = 65
        elif energy_cov < 0.15:
            scores["energy_consistency"] = 40   # whisper-flat
        else:
            scores["energy_consistency"] = 30   # very erratic volume

        # ================================================================== #
        # 5. PAUSE PATTERN  (long silence detection)                          #
        #    Confident: few long pauses (>1.5 s); short pauses OK             #
        # ================================================================== #
        frame_duration = hop_length / sr          # seconds per frame
        silence_threshold_db = np.percentile(rms_db, 25)
        is_silent = rms_db < silence_threshold_db

        # Find runs of silence
        long_pause_count = 0
        run_len = 0
        long_pause_threshold_frames = int(1.5 / frame_duration)

        for s in is_silent:
            if s:
                run_len += 1
                if run_len == long_pause_threshold_frames:
                    long_pause_count += 1
            else:
                run_len = 0

        pauses_per_minute = long_pause_count / (duration / 60.0 + 1e-6)

        if pauses_per_minute <= 2:
            scores["pause_pattern"] = 100
        elif pauses_per_minute <= 5:
            scores["pause_pattern"] = 75
        elif pauses_per_minute <= 9:
            scores["pause_pattern"] = 45
        else:
            scores["pause_pattern"] = 20

        # ================================================================== #
        # 6. JITTER  (pitch micro-instability, proxy for vocal tremor)        #
        #    Nervous/stressed speakers show more jitter                        #
        # ================================================================== #
        if len(voiced_f0) > 10:
            f0_diff = np.abs(np.diff(voiced_f0))
            jitter = np.mean(f0_diff) / (np.mean(voiced_f0) + 1e-6)
            if jitter < 0.01:
                scores["jitter"] = 100
            elif jitter < 0.03:
                scores["jitter"] = 75
            elif jitter < 0.06:
                scores["jitter"] = 50
            else:
                scores["jitter"] = 20
        else:
            scores["jitter"] = 40

        # ================================================================== #
        # 7. SPECTRAL CENTROID STABILITY  (timbre consistency)                #
        #    Confident voice → stable brightness; anxious → erratic           #
        # ================================================================== #
        centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        centroid_cov = np.std(centroid) / (np.mean(centroid) + 1e-6)

        if centroid_cov < 0.20:
            scores["spectral_stability"] = 100
        elif centroid_cov < 0.35:
            scores["spectral_stability"] = 75
        elif centroid_cov < 0.55:
            scores["spectral_stability"] = 50
        else:
            scores["spectral_stability"] = 25

        # ================================================================== #
        # WEIGHTED AGGREGATION                                                 #
        # ================================================================== #
        weights = {
            "speech_rate":        0.18,
            "pitch_variability":  0.16,
            "pitch_range":        0.12,
            "voiced_ratio":       0.15,
            "energy_consistency": 0.13,
            "pause_pattern":      0.14,
            "jitter":             0.07,
            "spectral_stability": 0.05,
        }

        final_score = sum(scores[k] * weights[k] for k in weights)
        final_score = round(min(max(final_score, 0), 100), 2)

        return final_score
    # ==========================================================
    # 🏆 SCORING SYSTEM 
    # ==========================================================
    def _compute_phase1_quality_score(self, speech, linguistic, prosodic_confidence):
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

        # 5. Prosodic Confidence (Acoustic/DSP Impact)
        # Assuming prosodic_confidence is a 0-100 float from your new function
        if prosodic_confidence < cfg.prosodic_confidence_low:
            score -= cfg.penalty_prosodic_high
        elif prosodic_confidence < cfg.prosodic_confidence_med:
            score -= cfg.penalty_prosodic_med

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
            y, sr, duration = self._load_audio()
            transcript = self._transcribe_audio()
            text = transcript.get("text", "").strip()
            
            if not text:
                logger.warning("Transcript is empty. Returning default metrics.")
                return {"error": "Empty transcript", "score": 0}

            # Extract metrics
            speech_metrics, words = self._extract_speech_metrics(transcript, duration)
            linguistic_metrics = self._extract_linguistic_metrics(text)
            prosodic_confidence_score = self.prosodic_confidence(y,sr,duration)

            # Compute Score
            phase1_score = self._compute_phase1_quality_score(
                speech=speech_metrics,
                linguistic=linguistic_metrics,
                prosodic_confidence = prosodic_confidence_score
            )

            logger.info(f"NLP Analysis Complete. Score: {phase1_score}/100")
            
            return {
                "transcript": text,
                "speech_metrics": speech_metrics,
                "linguistic_metrics": linguistic_metrics,
                "phase1_quality_score": phase1_score,
                "prosodic_confidence": prosodic_confidence_score,
                "phase": "phase_1",
                "version": "v1.0"
            }
            
        except Exception as e:
            logger.error(f"NLP Analysis Failed: {e}")
            raise e