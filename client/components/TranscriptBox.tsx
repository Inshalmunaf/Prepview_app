type Props = {
    transcript: string;
  };
  
  export default function TranscriptBox({ transcript }: Props) {
    return (
      <div className="mt-6 rounded-xl bg-slate-900 p-5 text-sm text-emerald-400 font-mono">
        <p className="opacity-80">Transcript Preview</p>
        <p className="mt-2 text-slate-200 leading-relaxed">
          {transcript}
        </p>
      </div>
    );
  }
  