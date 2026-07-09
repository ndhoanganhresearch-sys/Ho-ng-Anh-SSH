# Discussion Draft

#paper #discussion #draft

## Interpretation of benchmark results

The T0-T5 benchmark shows that the Step 6 workflow can recover cumulative crown deformation with high numerical accuracy in a controlled synthetic tunnel dataset. The expected crown maximum increases from `5 mm` at T1 to `45 mm` at T5, and the measured values follow the same monotonic trend.

The final T0-T5 comparison measured `44.05 mm` against an expected `45.00 mm`, corresponding to an absolute error of `0.95 mm`. The T3 and T4 comparisons also remained below `1 mm` absolute crown-maximum error, while T1 and T2 matched the expected crown maxima exactly in the benchmark output.

## Evidence from figures

The overview and crown profile figures provide visual confirmation of the time-series deformation trend, while the M3C2 heatmap provides spatial evidence for the deformation distribution between T0 and T5. These figures support the numeric benchmark table and make the result easier to inspect in a paper or technical report.

## Meaning of the result

The result supports a controlled validation claim: the workflow can track known synthetic crown deformation across multiple epochs. It does not yet prove field robustness under all tunnel monitoring conditions. The strongest current claim is therefore about reproducible synthetic validation, not operational deployment.

## Practical implications

A validated synthetic benchmark is useful because it provides a repeatable test bed for future changes to registration, centerline extraction, deformation metrics, and visualization. If future code changes degrade the T0-T5 benchmark, the evidence chain in Obsidian can identify which claim or figure is affected.

## Links

- [[Step 6 Benchmark Table]]
- [[Figure Captions]]
- [[Limitations Draft]]
- [[Research Claims]]
