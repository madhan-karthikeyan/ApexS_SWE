type Props = { current: string; steps: string[] }

export default function ProgressStepper({ current, steps }: Props) {
  const currentIndex = Math.max(steps.indexOf(current), 0)

  return (
    <div className="steps-list">
      {steps.map((step, index) => (
        <div className={`step-card ${index === currentIndex ? 'current' : index < currentIndex ? 'done' : ''}`} key={step}>
          <div className="step">
            <span className={`dot ${index === currentIndex ? 'active' : index < currentIndex ? 'done' : ''}`} />
            <span style={{ textTransform: 'capitalize', fontWeight: 600 }}>{step}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
