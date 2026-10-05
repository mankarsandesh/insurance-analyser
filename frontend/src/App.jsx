import { useState } from "react";

const EXAMPLE_REQUIREMENT =
  "We recently purchased a detached house in Surrey worth £3.5M. The property includes a swimming pool, " +
  "a separate garage, a home office and a garden studio. We own several pieces of jewellery and artwork. " +
  "We also employ a live-in nanny.";

export default function App() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function handleAnalyse() {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch("/api/analyse", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(typeof data.detail === "string" ? data.detail : "The request was rejected.");
      }
      setResult(data);
    } catch (err) {
      setError(err.message || "Could not reach the server. Check that the backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <header className="header">
        <h1>Insurance requirement analyser</h1>
        <p>
          Describe what the customer needs to insure. Amazon Comprehend finds the entities, then
          Amazon Bedrock maps them to the unified insurance schema.
        </p>
      </header>

      <section className="panel">
        <label htmlFor="requirement" className="field-label">
          Customer requirement
        </label>
        <textarea
          id="requirement"
          rows={6}
          maxLength={5000}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. We run a bakery in Leeds with 12 staff and two delivery vans…"
        />
        <div className="actions">
          <button className="primary" onClick={handleAnalyse} disabled={loading || !text.trim()}>
            {loading ? "Analysing…" : "Analyse requirement"}
          </button>
          <button className="secondary" onClick={() => setText(EXAMPLE_REQUIREMENT)} disabled={loading}>
            Use example
          </button>
          <span className="char-count">{text.length} / 5000</span>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {result && (
        <div className="results">
          <ComprehendResults entities={result.comprehend.entities} />
          <BedrockResults bedrock={result.bedrock} />
        </div>
      )}
    </div>
  );
}

function ComprehendResults({ entities }) {
  return (
    <section className="panel">
      <h2>Amazon Comprehend entities</h2>
      <p className="subtle">{entities.length} entities detected</p>
      {entities.length === 0 ? (
        <p>No entities found. Try adding places, amounts or named items.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Text</th>
                <th>Type</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((entity, index) => (
                <tr key={index}>
                  <td>{entity.text}</td>
                  <td>
                    <span className="tag">{entity.type}</span>
                  </td>
                  <td>{(entity.score * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function BedrockResults({ bedrock }) {
  const [copied, setCopied] = useState(false);
  const json = JSON.stringify(bedrock.profile, null, 2);

  async function handleCopy() {
    await navigator.clipboard.writeText(json);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Amazon Bedrock customer profile</h2>
        <button className="secondary small" onClick={handleCopy}>
          {copied ? "Copied" : "Copy JSON"}
        </button>
      </div>
      <p className="subtle">Model: {bedrock.model_id}</p>

      {bedrock.schema_errors.length === 0 ? (
        <p className="valid">Matches the unified insurance schema.</p>
      ) : (
        <div className="warning">
          <p>The profile doesn't fully match the schema:</p>
          <ul>
            {bedrock.schema_errors.map((message, index) => (
              <li key={index}>{message}</li>
            ))}
          </ul>
        </div>
      )}

      <pre className="json">{json}</pre>
    </section>
  );
}
