export function Logo({ mark = false }: { mark?: boolean }) {
  return (
    <span className={mark ? "logo logo-mark-only" : "logo"}>
      <svg className="logo-mark" viewBox="0 0 48 48" aria-hidden="true">
        <rect width="48" height="48" rx="12" fill="#4F46E5" />
        <circle cx="15" cy="15" r="4.2" fill="none" stroke="#fff" strokeWidth="2.4" />
        <path
          d="M19.2 15 H30 V28"
          fill="none"
          stroke="#fff"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M30 28 L36.5 35.2 L30 42.4 L23.5 35.2 Z"
          fill="none"
          stroke="#fff"
          strokeWidth="2.4"
          strokeLinejoin="round"
        />
      </svg>
      {mark ? null : (
        <span className="logo-words">
          <span className="logo-name">Aulivana</span>
          <span className="logo-sub">FCDesign</span>
        </span>
      )}
    </span>
  )
}
