type Props = {
    label: string;
    value: string;
  };
  
  export default function MetricCard({ label, value }: Props) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm border border-slate-200">
        <p className="text-sm text-slate-500">{label}</p>
        <h3 className="mt-2 text-2xl font-semibold text-slate-900">
          {value}
        </h3>
      </div>
    );
  }
  