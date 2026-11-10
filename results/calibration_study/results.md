# Calibration study results (auto-generated)

Manifest SHA-256: `f407448b540e007a202fc861346c784c10749f617d9f80b98a2bae53b8051999`. Bootstrap: 1000 draws resampling whole journey groups (seeds).

## Noise magnitude on test journeys

| Scenario | Trajectories | Mean radial GPS RMSE (m) | Mean RMSE inside burst (m) |
|---|---:|---:|---:|
| independent | 36 | 11.29 | n/a |
| burst | 36 | 15.42 | 23.45 |
| burst_diagonal | 36 | 18.44 | 30.69 |
| burst_negative | 36 | 16.79 | 26.77 |
| burst_long | 36 | 22.33 | 30.34 |
| matched_iid | 36 | 15.42 | n/a |
| gap | 36 | 11.33 | n/a |

Failed trajectories across all runs: 0.

## Model: baseline

### Calibrators (fitted on calibration journeys only)

| Map | Trajectories | Matched rows used | Unmatched excluded | Parameters |
|---|---:|---:|---:|---|
| platt_independent | 36 | 1390 | 0 | a=1.547, b=0.134 |
| isotonic_independent | 36 | 1390 | 0 | 15 steps |
| platt_mixture | 36 | 1390 | 0 | a=0.303, b=0.255 |
| isotonic_mixture | 36 | 1390 | 0 | 12 steps |

### End-to-end assignment quality on test

| Scenario | Obs | Matched | Accuracy (95% CI) | Nearest | Candidate recall | Failed traj. |
|---|---:|---:|---|---:|---:|---:|
| independent | 1384 | 100.00% | 89.74% [0.883, 0.911] | 82.51% | 100.00% | 0 |
| burst | 1384 | 100.00% | 80.27% [0.742, 0.857] | 73.70% | 100.00% | 0 |
| burst_diagonal | 1384 | 100.00% | 81.86% [0.803, 0.835] | 71.60% | 100.00% | 0 |
| burst_negative | 1384 | 100.00% | 73.55% [0.660, 0.807] | 72.83% | 100.00% | 0 |
| burst_long | 1384 | 100.00% | 61.34% [0.516, 0.710] | 65.32% | 100.00% | 0 |
| matched_iid | 1384 | 100.00% | 84.97% [0.829, 0.870] | 74.35% | 100.00% | 0 |
| gap | 1168 | 100.00% | 87.84% [0.861, 0.895] | 81.16% | 100.00% | 0 |
| ALL | 9472 | 100.00% | 79.76% [0.779, 0.817] | 74.35% | 100.00% | 0 |

### Probability quality on test (matched rows only; see matched fraction above)

| Scenario | Method | Brier (95% CI) | Δ Brier vs raw (95% CI) | Log loss | ECE |
|---|---|---|---|---:|---:|
| independent | raw | 0.0607 [0.0564, 0.0652] | — | 0.1875 | 0.0408 |
| independent | platt_independent | 0.0578 [0.0525, 0.0634] | -0.0029 [-0.0045, -0.0012] | 0.1765 | 0.0208 |
| independent | isotonic_independent | 0.0577 [0.0522, 0.0631] | -0.0030 [-0.0051, -0.0009] | 0.2192 | 0.0157 |
| independent | platt_mixture | 0.0756 [0.0721, 0.0795] | +0.0149 [0.0125, 0.0174] | 0.2533 | 0.0980 |
| independent | isotonic_mixture | 0.0671 [0.0626, 0.0717] | +0.0064 [0.0047, 0.0083] | 0.2377 | 0.0797 |
| burst | raw | 0.1119 [0.0798, 0.1484] | — | 0.3930 | 0.0391 |
| burst | platt_independent | 0.1180 [0.0801, 0.1592] | +0.0060 [-0.0009, 0.0140] | 0.4809 | 0.0746 |
| burst | isotonic_independent | 0.1217 [0.0831, 0.1638] | +0.0098 [0.0006, 0.0200] | 0.6394 | 0.0738 |
| burst | platt_mixture | 0.1190 [0.0944, 0.1471] | +0.0071 [-0.0024, 0.0166] | 0.3675 | 0.0717 |
| burst | isotonic_mixture | 0.1166 [0.0881, 0.1479] | +0.0047 [-0.0036, 0.0115] | 0.3667 | 0.0263 |
| burst_diagonal | raw | 0.0961 [0.0865, 0.1058] | — | 0.3046 | 0.0339 |
| burst_diagonal | platt_independent | 0.0980 [0.0873, 0.1085] | +0.0020 [0.0002, 0.0037] | 0.3452 | 0.0486 |
| burst_diagonal | isotonic_independent | 0.0995 [0.0889, 0.1098] | +0.0034 [0.0011, 0.0054] | 0.5303 | 0.0487 |
| burst_diagonal | platt_mixture | 0.1062 [0.0991, 0.1129] | +0.0101 [0.0058, 0.0141] | 0.3298 | 0.0876 |
| burst_diagonal | isotonic_mixture | 0.0978 [0.0907, 0.1052] | +0.0017 [-0.0017, 0.0051] | 0.3244 | 0.0424 |
| burst_negative | raw | 0.1842 [0.1288, 0.2449] | — | 0.8726 | 0.1254 |
| burst_negative | platt_independent | 0.1921 [0.1320, 0.2570] | +0.0079 [0.0025, 0.0135] | 1.1476 | 0.1516 |
| burst_negative | isotonic_independent | 0.1941 [0.1338, 0.2606] | +0.0099 [0.0039, 0.0169] | 1.7223 | 0.1534 |
| burst_negative | platt_mixture | 0.1697 [0.1290, 0.2163] | -0.0145 [-0.0305, 0.0005] | 0.5234 | 0.0873 |
| burst_negative | isotonic_mixture | 0.1678 [0.1240, 0.2170] | -0.0164 [-0.0300, -0.0040] | 0.7034 | 0.0705 |
| burst_long | raw | 0.2920 [0.2069, 0.3772] | — | 2.1776 | 0.2438 |
| burst_long | platt_independent | 0.3023 [0.2119, 0.3923] | +0.0102 [0.0055, 0.0149] | 2.5967 | 0.2701 |
| burst_long | isotonic_independent | 0.3049 [0.2145, 0.3946] | +0.0129 [0.0076, 0.0181] | 3.2015 | 0.2721 |
| burst_long | platt_mixture | 0.2713 [0.2006, 0.3417] | -0.0208 [-0.0359, -0.0059] | 0.9394 | 0.1925 |
| burst_long | isotonic_mixture | 0.2730 [0.1975, 0.3477] | -0.0190 [-0.0295, -0.0082] | 1.8905 | 0.1995 |
| matched_iid | raw | 0.0800 [0.0727, 0.0879] | — | 0.2493 | 0.0333 |
| matched_iid | platt_independent | 0.0802 [0.0713, 0.0900] | +0.0002 [-0.0018, 0.0023] | 0.2670 | 0.0282 |
| matched_iid | isotonic_independent | 0.0809 [0.0718, 0.0908] | +0.0009 [-0.0018, 0.0034] | 0.3649 | 0.0321 |
| matched_iid | platt_mixture | 0.0923 [0.0863, 0.0991] | +0.0123 [0.0093, 0.0151] | 0.2937 | 0.0900 |
| matched_iid | isotonic_mixture | 0.0835 [0.0766, 0.0907] | +0.0035 [0.0009, 0.0059] | 0.2701 | 0.0466 |
| gap | raw | 0.0706 [0.0658, 0.0756] | — | 0.2173 | 0.0469 |
| gap | platt_independent | 0.0675 [0.0613, 0.0739] | -0.0031 [-0.0050, -0.0011] | 0.2057 | 0.0244 |
| gap | isotonic_independent | 0.0673 [0.0608, 0.0738] | -0.0034 [-0.0059, -0.0008] | 0.2560 | 0.0184 |
| gap | platt_mixture | 0.0873 [0.0834, 0.0916] | +0.0167 [0.0139, 0.0194] | 0.2877 | 0.1095 |
| gap | isotonic_mixture | 0.0773 [0.0722, 0.0824] | +0.0066 [0.0047, 0.0089] | 0.2704 | 0.0864 |
| ALL | raw | 0.1293 [0.1166, 0.1416] | — | 0.6382 | 0.0664 |
| ALL | platt_independent | 0.1323 [0.1182, 0.1455] | +0.0030 [0.0012, 0.0049] | 0.7580 | 0.0841 |
| ALL | isotonic_independent | 0.1338 [0.1198, 0.1472] | +0.0045 [0.0023, 0.0068] | 1.0073 | 0.0857 |
| ALL | platt_mixture | 0.1326 [0.1222, 0.1432] | +0.0034 [0.0003, 0.0067] | 0.4310 | 0.0741 |
| ALL | isotonic_mixture | 0.1273 [0.1164, 0.1381] | -0.0020 [-0.0043, 0.0006] | 0.5875 | 0.0325 |

### Selective prediction on test: accepted risk at matched coverage

| Scenario | Score | AURC | risk@50% | risk@60% | risk@70% | risk@80% | risk@90% |
|---|---|---:|---:|---:|---:|---:|---:|
| independent | raw_confidence | 0.0118 | 0.0000 | 0.0012 | 0.0041 | 0.0135 | 0.0554 |
| independent | entropy | 0.0124 | 0.0000 | 0.0012 | 0.0041 | 0.0226 | 0.0530 |
| independent | platt_mixture | 0.0118 | 0.0000 | 0.0012 | 0.0041 | 0.0135 | 0.0554 |
| independent | isotonic_mixture | 0.0152 | 0.0000 | 0.0127 | 0.0127 | 0.0167 | 0.0712 |
| burst | raw_confidence | 0.0519 | 0.0361 | 0.0421 | 0.0599 | 0.1002 | 0.1501 |
| burst | entropy | 0.0544 | 0.0390 | 0.0421 | 0.0753 | 0.1146 | 0.1509 |
| burst | platt_mixture | 0.0519 | 0.0361 | 0.0421 | 0.0599 | 0.1002 | 0.1501 |
| burst | isotonic_mixture | 0.0685 | 0.0898 | 0.0898 | 0.0898 | 0.1170 | 0.1609 |
| burst_diagonal | raw_confidence | 0.0377 | 0.0101 | 0.0313 | 0.0444 | 0.0767 | 0.1268 |
| burst_diagonal | entropy | 0.0382 | 0.0101 | 0.0301 | 0.0423 | 0.0821 | 0.1260 |
| burst_diagonal | platt_mixture | 0.0377 | 0.0101 | 0.0313 | 0.0444 | 0.0767 | 0.1268 |
| burst_diagonal | isotonic_mixture | 0.0465 | 0.0098 | 0.0548 | 0.0548 | 0.0842 | 0.1501 |
| burst_negative | raw_confidence | 0.1253 | 0.1272 | 0.1432 | 0.1775 | 0.1886 | 0.2223 |
| burst_negative | entropy | 0.1280 | 0.1257 | 0.1552 | 0.1796 | 0.2004 | 0.2271 |
| burst_negative | platt_mixture | 0.1300 | 0.1272 | 0.1432 | 0.1775 | 0.1886 | 0.2223 |
| burst_negative | isotonic_mixture | 0.1493 | 0.1231 | 0.1839 | 0.1839 | 0.1887 | 0.2324 |
| burst_long | raw_confidence | 0.3232 | 0.3353 | 0.3225 | 0.3209 | 0.3312 | 0.3587 |
| burst_long | entropy | 0.3270 | 0.3338 | 0.3285 | 0.3292 | 0.3484 | 0.3571 |
| burst_long | platt_mixture | 0.3352 | 0.3353 | 0.3225 | 0.3209 | 0.3312 | 0.3587 |
| burst_long | isotonic_mixture | 0.3342 | 0.3219 | 0.3290 | 0.3290 | 0.3306 | 0.3634 |
| matched_iid | raw_confidence | 0.0252 | 0.0043 | 0.0120 | 0.0237 | 0.0487 | 0.1003 |
| matched_iid | entropy | 0.0255 | 0.0043 | 0.0108 | 0.0237 | 0.0569 | 0.0875 |
| matched_iid | platt_mixture | 0.0252 | 0.0043 | 0.0120 | 0.0237 | 0.0487 | 0.1003 |
| matched_iid | isotonic_mixture | 0.0329 | 0.0039 | 0.0437 | 0.0437 | 0.0502 | 0.1095 |
| gap | raw_confidence | 0.0166 | 0.0000 | 0.0043 | 0.0061 | 0.0214 | 0.0760 |
| gap | entropy | 0.0174 | 0.0000 | 0.0043 | 0.0073 | 0.0374 | 0.0713 |
| gap | platt_mixture | 0.0166 | 0.0000 | 0.0043 | 0.0061 | 0.0214 | 0.0760 |
| gap | isotonic_mixture | 0.0213 | 0.0000 | 0.0157 | 0.0157 | 0.0283 | 0.0854 |
| ALL | raw_confidence | 0.0862 | 0.0731 | 0.0823 | 0.0924 | 0.1120 | 0.1565 |
| ALL | entropy | 0.0876 | 0.0733 | 0.0836 | 0.0967 | 0.1252 | 0.1554 |
| ALL | platt_mixture | 0.0883 | 0.0731 | 0.0823 | 0.0924 | 0.1120 | 0.1565 |
| ALL | isotonic_mixture | 0.0970 | 0.0722 | 0.1067 | 0.1067 | 0.1122 | 0.1660 |

### Threshold transfer (target accepted risk 5% on calibration)

| Rule | Threshold | Cal. coverage | Cal. risk | independent cov / risk | burst cov / risk | burst_diagonal cov / risk | burst_negative cov / risk | burst_long cov / risk | matched_iid cov / risk | gap cov / risk |
|---|---:|---:|---:|---|---|---|---|---|---|---|
| confidence_from_independent | 0.5419 | 85.25% | 4.98% | 86.13% / 3.19% | 84.18% / 12.53% | 81.58% / 8.15% | 84.39% / 19.95% | 84.61% / 33.90% | 85.04% / 6.97% | 83.73% / 3.89% |
| entropy_from_independent | 0.5001 | 79.28% | 4.99% | 79.84% / 2.08% | 76.16% / 9.87% | 74.35% / 6.12% | 76.95% / 18.87% | 78.40% / 34.19% | 78.76% / 5.05% | 76.71% / 2.57% |
| confidence_from_mixture | 0.9785 | 52.09% | 4.97% | 57.44% / 0.00% | 48.99% / 3.24% | 51.59% / 0.98% | 51.66% / 12.31% | 54.55% / 32.19% | 55.71% / 0.39% | 51.46% / 0.00% |
| entropy_from_mixture | 0.9268 | 51.87% | 4.99% | 56.86% / 0.00% | 48.55% / 3.42% | 50.65% / 1.00% | 51.45% / 13.34% | 53.83% / 32.35% | 54.99% / 0.39% | 50.77% / 0.00% |

### Route hold-out: calibrators fitted on routes (0, 1, 2), tested on routes (3, 4, 5)

| Test scenario | Map | Brier | Log loss | ECE | Matched rows |
|---|---|---:|---:|---:|---:|
| independent | raw | 0.0613 | 0.1883 | 0.0464 | 692 |
| independent | platt_independent_all_routes | 0.0595 | 0.1795 | 0.0351 | 692 |
| independent | platt_independent_routes_0_2 | 0.0595 | 0.1798 | 0.0311 | 692 |
| independent | platt_mixture_all_routes | 0.0768 | 0.2551 | 0.1124 | 692 |
| independent | platt_mixture_routes_0_2 | 0.0898 | 0.2993 | 0.1255 | 692 |
| burst | raw | 0.1045 | 0.4147 | 0.0789 | 692 |
| burst | platt_independent_all_routes | 0.1065 | 0.5209 | 0.0813 | 692 |
| burst | platt_independent_routes_0_2 | 0.1055 | 0.5076 | 0.0754 | 692 |
| burst | platt_mixture_all_routes | 0.1140 | 0.3575 | 0.1030 | 692 |
| burst | platt_mixture_routes_0_2 | 0.1210 | 0.3792 | 0.0763 | 692 |
| burst_long | raw | 0.2414 | 1.6988 | 0.1994 | 692 |
| burst_long | platt_independent_all_routes | 0.2495 | 2.0712 | 0.2246 | 692 |
| burst_long | platt_independent_routes_0_2 | 0.2474 | 2.0390 | 0.2186 | 692 |
| burst_long | platt_mixture_all_routes | 0.2304 | 0.7816 | 0.1645 | 692 |
| burst_long | platt_mixture_routes_0_2 | 0.2214 | 0.6937 | 0.1190 | 692 |

## Model: robust

### Calibrators (fitted on calibration journeys only)

| Map | Trajectories | Matched rows used | Unmatched excluded | Parameters |
|---|---:|---:|---:|---|
| platt_independent | 36 | 1390 | 0 | a=1.707, b=1.105 |
| isotonic_independent | 36 | 1390 | 0 | 10 steps |
| platt_mixture | 36 | 1390 | 0 | a=0.442, b=0.594 |
| isotonic_mixture | 36 | 1390 | 0 | 10 steps |

### End-to-end assignment quality on test

| Scenario | Obs | Matched | Accuracy (95% CI) | Nearest | Candidate recall | Failed traj. |
|---|---:|---:|---|---:|---:|---:|
| independent | 1384 | 100.00% | 93.93% [0.927, 0.950] | 82.51% | 100.00% | 0 |
| burst | 1384 | 100.00% | 89.23% [0.854, 0.925] | 73.70% | 100.00% | 0 |
| burst_diagonal | 1384 | 100.00% | 85.55% [0.833, 0.877] | 71.60% | 100.00% | 0 |
| burst_negative | 1384 | 100.00% | 78.47% [0.710, 0.854] | 72.83% | 100.00% | 0 |
| burst_long | 1384 | 100.00% | 63.95% [0.530, 0.744] | 65.32% | 100.00% | 0 |
| matched_iid | 1384 | 100.00% | 92.49% [0.909, 0.940] | 74.35% | 100.00% | 0 |
| gap | 1168 | 100.00% | 92.72% [0.914, 0.940] | 81.16% | 100.00% | 0 |
| ALL | 9472 | 100.00% | 85.02% [0.832, 0.867] | 74.35% | 100.00% | 0 |

### Probability quality on test (matched rows only; see matched fraction above)

| Scenario | Method | Brier (95% CI) | Δ Brier vs raw (95% CI) | Log loss | ECE |
|---|---|---|---|---:|---:|
| independent | raw | 0.0489 [0.0448, 0.0526] | — | 0.1556 | 0.0626 |
| independent | platt_independent | 0.0383 [0.0330, 0.0437] | -0.0106 [-0.0148, -0.0063] | 0.1189 | 0.0141 |
| independent | isotonic_independent | 0.0378 [0.0325, 0.0434] | -0.0111 [-0.0150, -0.0072] | 0.1308 | 0.0062 |
| independent | platt_mixture | 0.0475 [0.0435, 0.0516] | -0.0014 [-0.0045, 0.0018] | 0.1710 | 0.0703 |
| independent | isotonic_mixture | 0.0434 [0.0393, 0.0476] | -0.0055 [-0.0079, -0.0031] | 0.1665 | 0.0579 |
| burst | raw | 0.0797 [0.0584, 0.1112] | — | 0.2692 | 0.0520 |
| burst | platt_independent | 0.0756 [0.0506, 0.1112] | -0.0041 [-0.0117, 0.0031] | 0.3163 | 0.0443 |
| burst | isotonic_independent | 0.0762 [0.0510, 0.1110] | -0.0035 [-0.0107, 0.0038] | 0.4588 | 0.0451 |
| burst | platt_mixture | 0.0790 [0.0586, 0.1073] | -0.0007 [-0.0063, 0.0041] | 0.2644 | 0.0521 |
| burst | isotonic_mixture | 0.0745 [0.0542, 0.1037] | -0.0052 [-0.0095, -0.0011] | 0.2516 | 0.0349 |
| burst_diagonal | raw | 0.0804 [0.0721, 0.0899] | — | 0.2482 | 0.0397 |
| burst_diagonal | platt_independent | 0.0848 [0.0725, 0.0985] | +0.0044 [-0.0029, 0.0118] | 0.2740 | 0.0573 |
| burst_diagonal | isotonic_independent | 0.0879 [0.0752, 0.1023] | +0.0075 [0.0007, 0.0147] | 0.4071 | 0.0627 |
| burst_diagonal | platt_mixture | 0.0867 [0.0777, 0.0967] | +0.0063 [-0.0002, 0.0124] | 0.2732 | 0.0686 |
| burst_diagonal | isotonic_mixture | 0.0832 [0.0732, 0.0951] | +0.0028 [-0.0011, 0.0072] | 0.3072 | 0.0427 |
| burst_negative | raw | 0.1498 [0.1060, 0.2000] | — | 0.5250 | 0.0903 |
| burst_negative | platt_independent | 0.1683 [0.1120, 0.2320] | +0.0185 [0.0002, 0.0387] | 0.8363 | 0.1400 |
| burst_negative | isotonic_independent | 0.1726 [0.1150, 0.2369] | +0.0228 [0.0039, 0.0450] | 1.3894 | 0.1454 |
| burst_negative | platt_mixture | 0.1448 [0.1026, 0.1912] | -0.0050 [-0.0173, 0.0046] | 0.4428 | 0.0586 |
| burst_negative | isotonic_mixture | 0.1524 [0.1064, 0.2032] | +0.0026 [-0.0075, 0.0145] | 0.4920 | 0.0828 |
| burst_long | raw | 0.2833 [0.2029, 0.3647] | — | 1.4860 | 0.2178 |
| burst_long | platt_independent | 0.3121 [0.2164, 0.4125] | +0.0288 [0.0118, 0.0466] | 2.3978 | 0.2942 |
| burst_long | isotonic_independent | 0.3145 [0.2181, 0.4161] | +0.0312 [0.0137, 0.0496] | 3.2463 | 0.2943 |
| burst_long | platt_mixture | 0.2718 [0.1948, 0.3495] | -0.0115 [-0.0180, -0.0053] | 0.9544 | 0.2116 |
| burst_long | isotonic_mixture | 0.2771 [0.1970, 0.3601] | -0.0062 [-0.0106, -0.0012] | 1.4478 | 0.2219 |
| matched_iid | raw | 0.0634 [0.0578, 0.0689] | — | 0.1943 | 0.0676 |
| matched_iid | platt_independent | 0.0524 [0.0442, 0.0608] | -0.0110 [-0.0168, -0.0054] | 0.1637 | 0.0168 |
| matched_iid | isotonic_independent | 0.0527 [0.0449, 0.0611] | -0.0107 [-0.0163, -0.0052] | 0.1858 | 0.0194 |
| matched_iid | platt_mixture | 0.0589 [0.0529, 0.0649] | -0.0045 [-0.0082, -0.0008] | 0.2030 | 0.0596 |
| matched_iid | isotonic_mixture | 0.0583 [0.0517, 0.0650] | -0.0051 [-0.0084, -0.0017] | 0.1991 | 0.0542 |
| gap | raw | 0.0591 [0.0543, 0.0634] | — | 0.1876 | 0.0746 |
| gap | platt_independent | 0.0460 [0.0398, 0.0524] | -0.0131 [-0.0181, -0.0080] | 0.1431 | 0.0116 |
| gap | isotonic_independent | 0.0458 [0.0393, 0.0525] | -0.0133 [-0.0181, -0.0083] | 0.1674 | 0.0081 |
| gap | platt_mixture | 0.0571 [0.0524, 0.0619] | -0.0020 [-0.0054, 0.0014] | 0.2020 | 0.0810 |
| gap | isotonic_mixture | 0.0522 [0.0468, 0.0574] | -0.0069 [-0.0096, -0.0042] | 0.1963 | 0.0677 |
| ALL | raw | 0.1104 [0.0988, 0.1225] | — | 0.4437 | 0.0665 |
| ALL | platt_independent | 0.1125 [0.0990, 0.1266] | +0.0022 [-0.0022, 0.0068] | 0.6177 | 0.0799 |
| ALL | isotonic_independent | 0.1140 [0.1005, 0.1281] | +0.0037 [-0.0004, 0.0079] | 0.8708 | 0.0836 |
| ALL | platt_mixture | 0.1077 [0.0968, 0.1193] | -0.0027 [-0.0062, 0.0004] | 0.3623 | 0.0390 |
| ALL | isotonic_mixture | 0.1071 [0.0959, 0.1185] | -0.0033 [-0.0058, -0.0009] | 0.4427 | 0.0215 |

### Selective prediction on test: accepted risk at matched coverage

| Scenario | Score | AURC | risk@50% | risk@60% | risk@70% | risk@80% | risk@90% |
|---|---|---:|---:|---:|---:|---:|---:|
| independent | raw_confidence | 0.0049 | 0.0000 | 0.0000 | 0.0010 | 0.0018 | 0.0233 |
| independent | entropy | 0.0055 | 0.0000 | 0.0000 | 0.0010 | 0.0027 | 0.0209 |
| independent | platt_mixture | 0.0049 | 0.0000 | 0.0000 | 0.0010 | 0.0018 | 0.0233 |
| independent | isotonic_mixture | 0.0074 | 0.0000 | 0.0000 | 0.0092 | 0.0092 | 0.0398 |
| burst | raw_confidence | 0.0238 | 0.0231 | 0.0205 | 0.0299 | 0.0361 | 0.0706 |
| burst | entropy | 0.0244 | 0.0217 | 0.0205 | 0.0310 | 0.0469 | 0.0626 |
| burst | platt_mixture | 0.0238 | 0.0231 | 0.0205 | 0.0299 | 0.0361 | 0.0706 |
| burst | isotonic_mixture | 0.0316 | 0.0233 | 0.0200 | 0.0465 | 0.0465 | 0.0847 |
| burst_diagonal | raw_confidence | 0.0237 | 0.0029 | 0.0108 | 0.0165 | 0.0505 | 0.0859 |
| burst_diagonal | entropy | 0.0238 | 0.0043 | 0.0108 | 0.0206 | 0.0496 | 0.0843 |
| burst_diagonal | platt_mixture | 0.0237 | 0.0029 | 0.0108 | 0.0165 | 0.0505 | 0.0859 |
| burst_diagonal | isotonic_mixture | 0.0331 | 0.0042 | 0.0415 | 0.0415 | 0.0551 | 0.0949 |
| burst_negative | raw_confidence | 0.0814 | 0.0679 | 0.1047 | 0.1135 | 0.1516 | 0.1822 |
| burst_negative | entropy | 0.0831 | 0.0679 | 0.1071 | 0.1300 | 0.1606 | 0.1685 |
| burst_negative | platt_mixture | 0.0814 | 0.0679 | 0.1047 | 0.1135 | 0.1516 | 0.1822 |
| burst_negative | isotonic_mixture | 0.0978 | 0.1010 | 0.1567 | 0.1567 | 0.1567 | 0.1943 |
| burst_long | raw_confidence | 0.2906 | 0.2962 | 0.3081 | 0.3168 | 0.3222 | 0.3355 |
| burst_long | entropy | 0.2945 | 0.3064 | 0.3177 | 0.3179 | 0.3384 | 0.3387 |
| burst_long | platt_mixture | 0.2910 | 0.2962 | 0.3081 | 0.3168 | 0.3222 | 0.3355 |
| burst_long | isotonic_mixture | 0.3081 | 0.2958 | 0.3094 | 0.3298 | 0.3298 | 0.3465 |
| matched_iid | raw_confidence | 0.0090 | 0.0000 | 0.0000 | 0.0021 | 0.0135 | 0.0393 |
| matched_iid | entropy | 0.0090 | 0.0000 | 0.0000 | 0.0021 | 0.0181 | 0.0353 |
| matched_iid | platt_mixture | 0.0090 | 0.0000 | 0.0000 | 0.0021 | 0.0135 | 0.0393 |
| matched_iid | isotonic_mixture | 0.0136 | 0.0000 | 0.0000 | 0.0225 | 0.0225 | 0.0556 |
| gap | raw_confidence | 0.0073 | 0.0000 | 0.0014 | 0.0012 | 0.0053 | 0.0371 |
| gap | entropy | 0.0080 | 0.0000 | 0.0014 | 0.0012 | 0.0171 | 0.0304 |
| gap | platt_mixture | 0.0073 | 0.0000 | 0.0014 | 0.0012 | 0.0053 | 0.0371 |
| gap | isotonic_mixture | 0.0108 | 0.0000 | 0.0014 | 0.0113 | 0.0113 | 0.0477 |
| ALL | raw_confidence | 0.0584 | 0.0505 | 0.0614 | 0.0692 | 0.0822 | 0.1097 |
| ALL | entropy | 0.0593 | 0.0511 | 0.0616 | 0.0706 | 0.0918 | 0.1058 |
| ALL | platt_mixture | 0.0583 | 0.0505 | 0.0614 | 0.0692 | 0.0822 | 0.1097 |
| ALL | isotonic_mixture | 0.0680 | 0.0526 | 0.0624 | 0.0894 | 0.0894 | 0.1249 |

### Threshold transfer (target accepted risk 5% on calibration)

| Rule | Threshold | Cal. coverage | Cal. risk | independent cov / risk | burst cov / risk | burst_diagonal cov / risk | burst_negative cov / risk | burst_long cov / risk | matched_iid cov / risk | gap cov / risk |
|---|---:|---:|---:|---|---|---|---|---|---|---|
| confidence_from_independent | 0.3418 | 98.27% | 4.98% | 97.76% / 4.80% | 97.83% / 9.82% | 95.45% / 12.04% | 96.68% / 20.18% | 97.69% / 35.65% | 97.76% / 6.43% | 97.43% / 5.71% |
| entropy_from_independent | 0.2021 | 97.41% | 4.95% | 97.98% / 5.31% | 96.82% / 9.55% | 96.24% / 12.54% | 94.80% / 19.13% | 95.23% / 34.98% | 96.10% / 5.79% | 97.43% / 6.33% |
| confidence_from_mixture | 0.9149 | 63.17% | 4.90% | 69.15% / 0.10% | 61.49% / 2.00% | 59.39% / 1.09% | 58.89% / 10.18% | 60.48% / 30.94% | 64.60% / 0.00% | 62.76% / 0.14% |
| entropy_from_mixture | 0.7515 | 63.53% | 4.98% | 70.16% / 0.10% | 62.07% / 2.10% | 60.12% / 1.08% | 59.25% / 10.37% | 61.05% / 31.48% | 65.17% / 0.22% | 63.78% / 0.13% |

### Route hold-out: calibrators fitted on routes (0, 1, 2), tested on routes (3, 4, 5)

| Test scenario | Map | Brier | Log loss | ECE | Matched rows |
|---|---|---:|---:|---:|---:|
| independent | raw | 0.0471 | 0.1506 | 0.0556 | 692 |
| independent | platt_independent_all_routes | 0.0398 | 0.1197 | 0.0174 | 692 |
| independent | platt_independent_routes_0_2 | 0.0418 | 0.1249 | 0.0227 | 692 |
| independent | platt_mixture_all_routes | 0.0484 | 0.1717 | 0.0698 | 692 |
| independent | platt_mixture_routes_0_2 | 0.0501 | 0.1794 | 0.0797 | 692 |
| burst | raw | 0.0824 | 0.2992 | 0.0652 | 692 |
| burst | platt_independent_all_routes | 0.0763 | 0.3873 | 0.0518 | 692 |
| burst | platt_independent_routes_0_2 | 0.0779 | 0.3830 | 0.0600 | 692 |
| burst | platt_mixture_all_routes | 0.0790 | 0.2680 | 0.0632 | 692 |
| burst | platt_mixture_routes_0_2 | 0.0804 | 0.2722 | 0.0653 | 692 |
| burst_long | raw | 0.2340 | 0.9778 | 0.1804 | 692 |
| burst_long | platt_independent_all_routes | 0.2643 | 1.6823 | 0.2530 | 692 |
| burst_long | platt_independent_routes_0_2 | 0.2690 | 1.6633 | 0.2584 | 692 |
| burst_long | platt_mixture_all_routes | 0.2228 | 0.7037 | 0.1594 | 692 |
| burst_long | platt_mixture_routes_0_2 | 0.2187 | 0.6811 | 0.1466 | 692 |

## Screening-slack sensitivity (development journeys, baseline)

| Slack multiplier / scenario | Matched | Accuracy | Accuracy given match | Failed traj. |
|---|---:|---:|---:|---:|
| 0/independent | 75.00% | 68.10% | 90.80% | 3/12 |
| 0/burst | 75.00% | 66.81% | 89.08% | 3/12 |
| 0/burst_long | 75.00% | 45.91% | 61.21% | 3/12 |
| 0/gap | 83.16% | 74.23% | 89.26% | 2/12 |
| 1/independent | 100.00% | 90.52% | 90.52% | 0/12 |
| 1/burst | 100.00% | 84.05% | 84.05% | 0/12 |
| 1/burst_long | 100.00% | 63.79% | 63.79% | 0/12 |
| 1/gap | 100.00% | 88.78% | 88.78% | 0/12 |
| 2/independent | 100.00% | 90.30% | 90.30% | 0/12 |
| 2/burst | 100.00% | 87.28% | 87.28% | 0/12 |
| 2/burst_long | 100.00% | 63.36% | 63.36% | 0/12 |
| 2/gap | 100.00% | 88.52% | 88.52% | 0/12 |
| 3/independent | 100.00% | 90.30% | 90.30% | 0/12 |
| 3/burst | 100.00% | 83.41% | 83.41% | 0/12 |
| 3/burst_long | 100.00% | 64.22% | 64.22% | 0/12 |
| 3/gap | 100.00% | 88.52% | 88.52% | 0/12 |
| 5/independent | 100.00% | 90.30% | 90.30% | 0/12 |
| 5/burst | 100.00% | 86.42% | 86.42% | 0/12 |
| 5/burst_long | 100.00% | 66.38% | 66.38% | 0/12 |
| 5/gap | 100.00% | 88.52% | 88.52% | 0/12 |
