// The one box every refusal on this screen renders in, whatever door sent it:
// a read, an answer, or starting a run. The sentence is always the server's
// own — this component never writes a second one in front of it.
export default function Refusal({ text }) {
  return (
    <p className="mb-8 border-2 border-danger bg-card px-5 py-4" role="alert">
      <span className="eyebrow mb-1 block text-danger">the server refused</span>
      {text}
    </p>
  );
}
