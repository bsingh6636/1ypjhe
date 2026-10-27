export default function Methodology({ snapshotId }: { snapshotId?: string }) {
  return (
    <details className="method">
      <summary>How this is computed</summary>
      <ul>
        <li>
          <strong>Eligibility.</strong> For each delivery hour, the forecast shown is the value from the latest
          Elexon WINDFOR publication with <code>publishTime</code> at or before the cutoff on the decision date. Later
          publications are never used, however accurate they turned out to be.
        </li>
        <li>
          <strong>Decision and delivery days.</strong> The decision is made on day D at the cutoff (UK local time);
          the delivery day is the whole of D+1 in UK time. January 2026 is GMT, so UK time equals UTC here.
        </li>
        <li>
          <strong>Alignment.</strong> WINDFOR is hourly, FUELHH actuals are half-hourly. Each forecast hour is compared
          with the mean of the two half-hour actuals in that hour. If either half-hour is missing the hour is
          excluded, not filled. Forecasts are never interpolated or duplicated.
        </li>
        <li>
          <strong>Error sign.</strong> error = forecast − actual. Positive means wind was over-forecast, which is the
          direction that leaves a buyer short of energy.
        </li>
        <li>
          <strong>Metrics.</strong> MAE, RMSE, bias and the 90th percentile of absolute error are pooled over all
          matched hours in the selection (not averaged across daily values). Coverage counts are always shown.
        </li>
        <li>
          <strong>Data.</strong> Elexon FUELHH (fuelType WIND) and WINDFOR via the public Insights API, frozen into an
          immutable snapshot{snapshotId ? ` ${snapshotId}` : ""}. Values are GB transmission-metered wind as reported
          by Elexon; embedded wind is not included.
        </li>
        <li>
          <strong>What this is not.</strong> A historical replay for January 2026 only. It does not forecast wind, and
          the month-level error statistics were not available to a trader during January; they are a retrospective
          evaluation.
        </li>
      </ul>
    </details>
  );
}
