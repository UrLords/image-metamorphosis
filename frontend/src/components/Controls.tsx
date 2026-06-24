interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  unit?: string;
  onChange: (v: number) => void;
}

export function Slider({
  label,
  value,
  min,
  max,
  step = 1,
  unit = "",
  onChange,
}: SliderProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-muted uppercase tracking-wider">
          {label}
        </label>
        <span className="text-sm font-semibold text-accent font-mono">
          {value}
          {unit}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
        style={{
          background: `linear-gradient(to right, #C9A86C ${((value - min) / (max - min)) * 100}%, #2A3340 0)`,
          accentColor: "#C9A86C",
        }}
      />
      <div className="flex justify-between text-xs text-muted/50 font-mono">
        <span>
          {min}
          {unit}
        </span>
        <span>
          {max}
          {unit}
        </span>
      </div>
    </div>
  );
}

interface SelectProps {
  label: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (v: string) => void;
}

export function Select({ label, value, options, onChange }: SelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted uppercase tracking-wider">
        {label}
      </label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-card border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-accent cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

interface ProcessButtonProps {
  onClick: () => void;
  isLoading: boolean;
  disabled?: boolean;
}

export function ProcessButton({
  onClick,
  isLoading,
  disabled,
}: ProcessButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={isLoading || disabled}
      className={`
        w-full py-3 rounded-xl font-semibold text-sm transition-all
        flex items-center justify-center gap-2
        ${
          isLoading || disabled
            ? "bg-accent/30 text-accent/50 cursor-not-allowed"
            : "bg-accent text-[#0C1014] hover:bg-accent/90 shadow-glow active:scale-[0.98]"
        }
      `}
    >
      {isLoading ? (
        <>
          <div className="w-4 h-4 border-2 border-[#0C1014]/40 border-t-[#0C1014] rounded-full animate-spin" />
          <span>Memproses...</span>
        </>
      ) : (
        <span>Proses Gambar</span>
      )}
    </button>
  );
}

interface ErrorBannerProps {
  message: string;
}

export function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3">
      <p className="text-sm text-red-400">Error: {message}</p>
    </div>
  );
}
