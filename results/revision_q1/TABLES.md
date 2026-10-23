# Retrospective robustness results

Source commit: `e7abad97107e918db8de5d51712923b55f0ba884`. Generated from saved predictions.

| Regime | Horizon | n | Rel. MAE | MASE candidate / persistence | 80% coverage | Rel. width | 95% block CI (28 d) | Holm p |
|---|---|---:|---:|---:|---:|---:|---|---:|
| cleaned | next | 553,801 | 0.951 | 1.098 / 1.156 | 0.777 | 0.217 | [0.946, 0.955] | 3.2e-90 |
| cleaned | h3 | 531,321 | 0.943 | 1.004 / 1.060 | 0.790 | 0.272 | [0.939, 0.947] | 1.1e-104 |
| cleaned | h7 | 519,251 | 0.952 | 1.071 / 1.109 | 0.795 | 0.342 | [0.949, 0.956] | 1.8e-62 |
| cleaned | h14 | 496,306 | 0.957 | 1.043 / 1.061 | 0.794 | 0.442 | [0.953, 0.962] | 2e-27 |
| unfiltered | next | 554,112 | 0.951 | 1.110 / 1.168 | 0.778 | 0.219 | [0.945, 0.955] | 2.5e-54 |
| unfiltered | h3 | 531,606 | 0.941 | 1.014 / 1.071 | 0.791 | 0.273 | [0.936, 0.946] | 3.1e-51 |
| unfiltered | h7 | 519,527 | 0.950 | 1.080 / 1.117 | 0.795 | 0.342 | [0.946, 0.954] | 6.3e-39 |
| unfiltered | h14 | 496,581 | 0.955 | 1.048 / 1.065 | 0.795 | 0.443 | [0.949, 0.960] | 4.7e-23 |

## All baselines

| Regime/horizon | Predictor | n | MAE | MASE | Relative MAE |
|---|---|---:|---:|---:|---:|
| cleaned_next | candidate | 553,801 | 192.30 | 1.098 | 0.951 |
| cleaned_next | persistence | 553,801 | 202.26 | 1.156 | 1.000 |
| cleaned_next | ma7 | 553,801 | 228.47 | 1.383 | 1.130 |
| cleaned_next | ma30 | 553,801 | 352.96 | 2.326 | 1.745 |
| cleaned_next | snaive | 553,801 | 805.01 | 8.182 | 3.980 |
| cleaned_next | sadj | 553,801 | 222.60 | 1.290 | 1.101 |
| cleaned_h3 | candidate | 531,321 | 238.50 | 1.004 | 0.943 |
| cleaned_h3 | persistence | 531,321 | 252.95 | 1.060 | 1.000 |
| cleaned_h3 | ma7 | 531,321 | 263.88 | 1.139 | 1.043 |
| cleaned_h3 | ma30 | 531,321 | 376.52 | 1.709 | 1.489 |
| cleaned_h3 | snaive | 531,321 | 808.25 | 5.452 | 3.195 |
| cleaned_h3 | sadj | 531,321 | 303.07 | 1.290 | 1.198 |
| cleaned_h7 | candidate | 519,251 | 302.15 | 1.071 | 0.952 |
| cleaned_h7 | persistence | 519,251 | 317.31 | 1.109 | 1.000 |
| cleaned_h7 | ma7 | 519,251 | 324.55 | 1.146 | 1.023 |
| cleaned_h7 | ma30 | 519,251 | 421.36 | 1.521 | 1.328 |
| cleaned_h7 | snaive | 519,251 | 812.53 | 4.232 | 2.561 |
| cleaned_h7 | sadj | 519,251 | 416.99 | 1.494 | 1.314 |
| cleaned_h14 | candidate | 496,306 | 393.83 | 1.043 | 0.957 |
| cleaned_h14 | persistence | 496,306 | 411.51 | 1.061 | 1.000 |
| cleaned_h14 | ma7 | 496,306 | 414.58 | 1.077 | 1.007 |
| cleaned_h14 | ma30 | 496,306 | 493.38 | 1.308 | 1.199 |
| cleaned_h14 | snaive | 496,306 | 817.48 | 3.072 | 1.987 |
| cleaned_h14 | sadj | 496,306 | 539.41 | 1.424 | 1.311 |
| unfiltered_next | candidate | 554,112 | 197.04 | 1.110 | 0.951 |
| unfiltered_next | persistence | 554,112 | 207.30 | 1.168 | 1.000 |
| unfiltered_next | ma7 | 554,112 | 232.78 | 1.394 | 1.123 |
| unfiltered_next | ma30 | 554,112 | 357.87 | 2.336 | 1.726 |
| unfiltered_next | snaive | 554,112 | 808.66 | 8.181 | 3.901 |
| unfiltered_next | sadj | 554,112 | 227.93 | 1.303 | 1.100 |
| unfiltered_h3 | candidate | 531,606 | 243.52 | 1.014 | 0.941 |
| unfiltered_h3 | persistence | 531,606 | 258.90 | 1.071 | 1.000 |
| unfiltered_h3 | ma7 | 531,606 | 267.38 | 1.146 | 1.033 |
| unfiltered_h3 | ma30 | 531,606 | 380.26 | 1.716 | 1.469 |
| unfiltered_h3 | snaive | 531,606 | 810.81 | 5.451 | 3.132 |
| unfiltered_h3 | sadj | 531,606 | 309.62 | 1.302 | 1.196 |
| unfiltered_h7 | candidate | 519,527 | 307.13 | 1.080 | 0.950 |
| unfiltered_h7 | persistence | 519,527 | 323.36 | 1.117 | 1.000 |
| unfiltered_h7 | ma7 | 519,527 | 328.04 | 1.151 | 1.014 |
| unfiltered_h7 | ma30 | 519,527 | 425.13 | 1.525 | 1.315 |
| unfiltered_h7 | snaive | 519,527 | 815.16 | 4.231 | 2.521 |
| unfiltered_h7 | sadj | 519,527 | 424.14 | 1.503 | 1.312 |
| unfiltered_h14 | candidate | 496,581 | 397.39 | 1.048 | 0.955 |
| unfiltered_h14 | persistence | 496,581 | 416.21 | 1.065 | 1.000 |
| unfiltered_h14 | ma7 | 496,581 | 416.52 | 1.078 | 1.001 |
| unfiltered_h14 | ma30 | 496,581 | 495.60 | 1.308 | 1.191 |
| unfiltered_h14 | snaive | 496,581 | 818.38 | 3.070 | 1.966 |
| unfiltered_h14 | sadj | 496,581 | 545.44 | 1.429 | 1.310 |

## Monthly and series uncertainty

| Regime/horizon | Entity cluster ratio 95% CI | Share series better | MAE difference 95% CI (28 days) | Seasonal fallbacks |
|---|---|---:|---|---:|
| cleaned_next | [0.9464686846346844, 0.955064867068772] | 0.606 | [-11.10855390993143, -8.851843085202285] | 57998 |

* cleaned_next, 2026-01: 69,039 rows; relative MAE 0.961
* cleaned_next, 2026-02: 60,811 rows; relative MAE 0.953
* cleaned_next, 2026-03: 64,111 rows; relative MAE 0.950
* cleaned_next, 2026-04: 69,328 rows; relative MAE 0.953
* cleaned_next, 2026-05: 64,997 rows; relative MAE 0.962
* cleaned_next, 2026-06: 50,959 rows; relative MAE 0.939
* cleaned_next, 2026-07: 51,765 rows; relative MAE 0.949
* cleaned_next, 2026-08: 50,249 rows; relative MAE 0.948
* cleaned_next, 2026-09: 43,679 rows; relative MAE 0.940
* cleaned_next, 2026-10: 28,863 rows; relative MAE 0.945
| cleaned_h3 | [0.9389713882614875, 0.9466170812362145] | 0.655 | [-15.718157413198313, -13.201356129998116] | 54314 |

* cleaned_h3, 2026-01: 65,741 rows; relative MAE 0.947
* cleaned_h3, 2026-02: 58,373 rows; relative MAE 0.945
* cleaned_h3, 2026-03: 61,660 rows; relative MAE 0.940
* cleaned_h3, 2026-04: 67,277 rows; relative MAE 0.949
* cleaned_h3, 2026-05: 62,132 rows; relative MAE 0.951
* cleaned_h3, 2026-06: 49,233 rows; relative MAE 0.933
* cleaned_h3, 2026-07: 50,550 rows; relative MAE 0.940
* cleaned_h3, 2026-08: 48,510 rows; relative MAE 0.938
* cleaned_h3, 2026-09: 42,208 rows; relative MAE 0.941
* cleaned_h3, 2026-10: 25,637 rows; relative MAE 0.941
| cleaned_h7 | [0.949409821695846, 0.9553250900930025] | 0.685 | [-16.377089030361866, -14.049004136188884] | 52869 |

* cleaned_h7, 2026-01: 63,761 rows; relative MAE 0.948
* cleaned_h7, 2026-02: 58,302 rows; relative MAE 0.955
* cleaned_h7, 2026-03: 61,306 rows; relative MAE 0.951
* cleaned_h7, 2026-04: 66,967 rows; relative MAE 0.954
* cleaned_h7, 2026-05: 59,704 rows; relative MAE 0.953
* cleaned_h7, 2026-06: 48,636 rows; relative MAE 0.947
* cleaned_h7, 2026-07: 50,361 rows; relative MAE 0.949
* cleaned_h7, 2026-08: 47,750 rows; relative MAE 0.949
* cleaned_h7, 2026-09: 42,103 rows; relative MAE 0.963
* cleaned_h7, 2026-10: 20,361 rows; relative MAE 0.959
| cleaned_h14 | [0.9538745407403367, 0.9600410282261506] | 0.680 | [-19.65060106270598, -15.675444040106706] | 49885 |

* cleaned_h14, 2026-01: 61,128 rows; relative MAE 0.948
* cleaned_h14, 2026-02: 57,989 rows; relative MAE 0.962
* cleaned_h14, 2026-03: 60,420 rows; relative MAE 0.952
* cleaned_h14, 2026-04: 66,347 rows; relative MAE 0.958
* cleaned_h14, 2026-05: 55,254 rows; relative MAE 0.954
* cleaned_h14, 2026-06: 47,503 rows; relative MAE 0.959
* cleaned_h14, 2026-07: 49,916 rows; relative MAE 0.956
* cleaned_h14, 2026-08: 45,932 rows; relative MAE 0.954
* cleaned_h14, 2026-09: 41,675 rows; relative MAE 0.971
* cleaned_h14, 2026-10: 10,142 rows; relative MAE 0.972
| unfiltered_next | [0.945936386070912, 0.9554939363560395] | 0.609 | [-11.659433879338012, -9.029688320805658] | 58038 |

* unfiltered_next, 2026-01: 69,125 rows; relative MAE 0.957
* unfiltered_next, 2026-02: 60,875 rows; relative MAE 0.952
* unfiltered_next, 2026-03: 64,123 rows; relative MAE 0.951
* unfiltered_next, 2026-04: 69,372 rows; relative MAE 0.954
* unfiltered_next, 2026-05: 65,011 rows; relative MAE 0.961
* unfiltered_next, 2026-06: 50,988 rows; relative MAE 0.940
* unfiltered_next, 2026-07: 51,802 rows; relative MAE 0.948
* unfiltered_next, 2026-08: 50,260 rows; relative MAE 0.948
* unfiltered_next, 2026-09: 43,684 rows; relative MAE 0.941
* unfiltered_next, 2026-10: 28,872 rows; relative MAE 0.944
| unfiltered_h3 | [0.935791697297653, 0.9451431076251685] | 0.652 | [-17.39681389757126, -13.705437708272727] | 54350 |

* unfiltered_h3, 2026-01: 65,818 rows; relative MAE 0.931
* unfiltered_h3, 2026-02: 58,425 rows; relative MAE 0.945
* unfiltered_h3, 2026-03: 61,669 rows; relative MAE 0.939
* unfiltered_h3, 2026-04: 67,319 rows; relative MAE 0.948
* unfiltered_h3, 2026-05: 62,146 rows; relative MAE 0.950
* unfiltered_h3, 2026-06: 49,261 rows; relative MAE 0.933
* unfiltered_h3, 2026-07: 50,586 rows; relative MAE 0.941
* unfiltered_h3, 2026-08: 48,521 rows; relative MAE 0.938
* unfiltered_h3, 2026-09: 42,213 rows; relative MAE 0.941
* unfiltered_h3, 2026-10: 25,648 rows; relative MAE 0.940
| unfiltered_h7 | [0.9463548359801844, 0.9533670010292539] | 0.676 | [-18.185916855414046, -14.598511564740326] | 52907 |

* unfiltered_h7, 2026-01: 63,826 rows; relative MAE 0.940
* unfiltered_h7, 2026-02: 58,357 rows; relative MAE 0.953
* unfiltered_h7, 2026-03: 61,320 rows; relative MAE 0.949
* unfiltered_h7, 2026-04: 67,005 rows; relative MAE 0.953
* unfiltered_h7, 2026-05: 59,719 rows; relative MAE 0.950
* unfiltered_h7, 2026-06: 48,665 rows; relative MAE 0.945
* unfiltered_h7, 2026-07: 50,397 rows; relative MAE 0.947
* unfiltered_h7, 2026-08: 47,758 rows; relative MAE 0.947
* unfiltered_h7, 2026-09: 42,109 rows; relative MAE 0.966
* unfiltered_h7, 2026-10: 20,371 rows; relative MAE 0.960
| unfiltered_h14 | [0.9515994219334365, 0.957946859745992] | 0.677 | [-21.655893424383642, -16.492283605814453] | 49904 |

* unfiltered_h14, 2026-01: 61,192 rows; relative MAE 0.942
* unfiltered_h14, 2026-02: 58,048 rows; relative MAE 0.962
* unfiltered_h14, 2026-03: 60,429 rows; relative MAE 0.950
* unfiltered_h14, 2026-04: 66,389 rows; relative MAE 0.957
* unfiltered_h14, 2026-05: 55,272 rows; relative MAE 0.952
* unfiltered_h14, 2026-06: 47,530 rows; relative MAE 0.960
* unfiltered_h14, 2026-07: 49,950 rows; relative MAE 0.956
* unfiltered_h14, 2026-08: 45,944 rows; relative MAE 0.949
* unfiltered_h14, 2026-09: 41,682 rows; relative MAE 0.968
* unfiltered_h14, 2026-10: 10,145 rows; relative MAE 0.970

## Common origins (targets and features may differ)

| Horizon | Regime | n | Rel. MAE | Coverage80 |
|---|---|---:|---:|---:|
| next | cleaned | 553,793 | 0.951 | 0.777 |
| next | unfiltered | 553,793 | 0.952 | 0.778 |
| h3 | cleaned | 531,316 | 0.943 | 0.790 |
| h3 | unfiltered | 531,316 | 0.944 | 0.791 |
| h7 | cleaned | 519,244 | 0.952 | 0.795 |
| h7 | unfiltered | 519,244 | 0.951 | 0.796 |
| h14 | cleaned | 496,298 | 0.957 | 0.794 |
| h14 | unfiltered | 496,298 | 0.956 | 0.795 |
