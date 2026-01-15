type Props = {
    title: string;
    children: React.ReactNode;
  };
  
  export default function Section({ title, children }: Props) {
    return (
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-800">
          {title}
        </h2>
        {children}
      </section>
    );
  }
  