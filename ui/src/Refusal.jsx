// The one box every refusal on this screen renders in, whatever door sent it:
// a read, an answer, or starting a run. The sentence is always the server's
// own — this component never writes a second one in front of it. The
// heading defaults to a general label; the Add-project box passes its own
// (screen 2: "the words 'the server refused' are gone" there).
export default function Refusal({ text, heading = "the server refused" }) {
  return (
    <p className="mb-8 border-2 border-danger bg-card px-5 py-4" role="alert">
      <span className="eyebrow mb-1 block text-danger">{heading}</span>
      {text}
    </p>
  );
}
