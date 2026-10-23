# Retrospective robustness results

Legacy HLN heuristic and 500-replicate intervals below are retained comparators, not primary release inference. See the complete dependence sensitivities below.

Source commit: `e233b4038feb78e9d92b8f4fdb6286e3b3e6509a`. Generated from saved predictions.

| Regime | Horizon | n | Rel. MAE | MASE candidate / persistence | 80% coverage | Rel. width | 95% block CI (28 d) | Holm p |
|---|---|---:|---:|---:|---:|---:|---|---:|
| cleaned | next | 553,793 | 0.951 | 1.100 / 1.156 | 0.777 | 0.217 | [0.947, 0.955] | 1e-92 |
| cleaned | h3 | 531,316 | 0.943 | 1.004 / 1.060 | 0.791 | 0.272 | [0.940, 0.947] | 6.1e-102 |
| cleaned | h7 | 519,244 | 0.950 | 1.074 / 1.109 | 0.794 | 0.338 | [0.946, 0.954] | 1.1e-54 |
| cleaned | h14 | 496,298 | 0.956 | 1.044 / 1.061 | 0.794 | 0.442 | [0.952, 0.961] | 7.3e-26 |
| unfiltered | next | 554,112 | 0.951 | 1.110 / 1.168 | 0.778 | 0.219 | [0.945, 0.955] | 2.5e-54 |
| unfiltered | h3 | 531,606 | 0.941 | 1.014 / 1.071 | 0.791 | 0.273 | [0.936, 0.946] | 3.1e-51 |
| unfiltered | h7 | 519,527 | 0.950 | 1.080 / 1.117 | 0.795 | 0.342 | [0.946, 0.954] | 6.3e-39 |
| unfiltered | h14 | 496,581 | 0.955 | 1.048 / 1.065 | 0.795 | 0.443 | [0.949, 0.960] | 4.7e-23 |

## All baselines

| Regime/horizon | Predictor | n | MAE | MASE | Relative MAE |
|---|---|---:|---:|---:|---:|
| cleaned_next | candidate | 553,793 | 192.34 | 1.100 | 0.951 |
| cleaned_next | persistence | 553,793 | 202.26 | 1.156 | 1.000 |
| cleaned_next | ma7 | 553,793 | 228.47 | 1.383 | 1.130 |
| cleaned_next | ma30 | 553,793 | 352.96 | 2.326 | 1.745 |
| cleaned_next | snaive | 553,793 | 805.02 | 8.182 | 3.980 |
| cleaned_next | sadj | 553,793 | 222.61 | 1.290 | 1.101 |
| cleaned_h3 | candidate | 531,316 | 238.61 | 1.004 | 0.943 |
| cleaned_h3 | persistence | 531,316 | 252.95 | 1.060 | 1.000 |
| cleaned_h3 | ma7 | 531,316 | 263.89 | 1.139 | 1.043 |
| cleaned_h3 | ma30 | 531,316 | 376.52 | 1.709 | 1.489 |
| cleaned_h3 | snaive | 531,316 | 808.25 | 5.452 | 3.195 |
| cleaned_h3 | sadj | 531,316 | 303.07 | 1.290 | 1.198 |
| cleaned_h7 | candidate | 519,244 | 301.36 | 1.074 | 0.950 |
| cleaned_h7 | persistence | 519,244 | 317.31 | 1.109 | 1.000 |
| cleaned_h7 | ma7 | 519,244 | 324.55 | 1.146 | 1.023 |
| cleaned_h7 | ma30 | 519,244 | 421.37 | 1.521 | 1.328 |
| cleaned_h7 | snaive | 519,244 | 812.54 | 4.232 | 2.561 |
| cleaned_h7 | sadj | 519,244 | 416.99 | 1.494 | 1.314 |
| cleaned_h14 | candidate | 496,298 | 393.48 | 1.044 | 0.956 |
| cleaned_h14 | persistence | 496,298 | 411.51 | 1.061 | 1.000 |
| cleaned_h14 | ma7 | 496,298 | 414.58 | 1.077 | 1.007 |
| cleaned_h14 | ma30 | 496,298 | 493.39 | 1.308 | 1.199 |
| cleaned_h14 | snaive | 496,298 | 817.49 | 3.072 | 1.987 |
| cleaned_h14 | sadj | 496,298 | 539.42 | 1.424 | 1.311 |
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
| cleaned_next | [0.946660486949663, 0.955269394169012] | 0.605 | [-11.057409068270921, -8.819724657294465] | 57990 |

* cleaned_next, 2026-01: 69,036 rows; relative MAE 0.960
* cleaned_next, 2026-02: 60,811 rows; relative MAE 0.953
* cleaned_next, 2026-03: 64,111 rows; relative MAE 0.952
* cleaned_next, 2026-04: 69,326 rows; relative MAE 0.953
* cleaned_next, 2026-05: 64,994 rows; relative MAE 0.962
* cleaned_next, 2026-06: 50,959 rows; relative MAE 0.940
* cleaned_next, 2026-07: 51,765 rows; relative MAE 0.949
* cleaned_next, 2026-08: 50,249 rows; relative MAE 0.947
* cleaned_next, 2026-09: 43,679 rows; relative MAE 0.942
* cleaned_next, 2026-10: 28,863 rows; relative MAE 0.944
| cleaned_h3 | [0.939314728490859, 0.9473399722696871] | 0.650 | [-15.579366983660147, -13.102969073847488] | 54309 |

* cleaned_h3, 2026-01: 65,740 rows; relative MAE 0.947
* cleaned_h3, 2026-02: 58,373 rows; relative MAE 0.947
* cleaned_h3, 2026-03: 61,660 rows; relative MAE 0.939
* cleaned_h3, 2026-04: 67,276 rows; relative MAE 0.949
* cleaned_h3, 2026-05: 62,129 rows; relative MAE 0.952
* cleaned_h3, 2026-06: 49,233 rows; relative MAE 0.934
* cleaned_h3, 2026-07: 50,550 rows; relative MAE 0.940
* cleaned_h3, 2026-08: 48,510 rows; relative MAE 0.938
* cleaned_h3, 2026-09: 42,208 rows; relative MAE 0.942
* cleaned_h3, 2026-10: 25,637 rows; relative MAE 0.940
| cleaned_h7 | [0.946339702074782, 0.9534066060978054] | 0.661 | [-17.501180202818404, -14.642115241688108] | 52862 |

* cleaned_h7, 2026-01: 63,758 rows; relative MAE 0.946
* cleaned_h7, 2026-02: 58,302 rows; relative MAE 0.955
* cleaned_h7, 2026-03: 61,306 rows; relative MAE 0.949
* cleaned_h7, 2026-04: 66,966 rows; relative MAE 0.952
* cleaned_h7, 2026-05: 59,701 rows; relative MAE 0.949
* cleaned_h7, 2026-06: 48,636 rows; relative MAE 0.942
* cleaned_h7, 2026-07: 50,361 rows; relative MAE 0.947
* cleaned_h7, 2026-08: 47,750 rows; relative MAE 0.942
* cleaned_h7, 2026-09: 42,103 rows; relative MAE 0.962
* cleaned_h7, 2026-10: 20,361 rows; relative MAE 0.960
| cleaned_h14 | [0.9534125375194772, 0.9590117813082618] | 0.675 | [-20.0683404113279, -15.891980713094892] | 49877 |

* cleaned_h14, 2026-01: 61,124 rows; relative MAE 0.949
* cleaned_h14, 2026-02: 57,989 rows; relative MAE 0.962
* cleaned_h14, 2026-03: 60,420 rows; relative MAE 0.950
* cleaned_h14, 2026-04: 66,346 rows; relative MAE 0.957
* cleaned_h14, 2026-05: 55,251 rows; relative MAE 0.948
* cleaned_h14, 2026-06: 47,503 rows; relative MAE 0.960
* cleaned_h14, 2026-07: 49,916 rows; relative MAE 0.957
* cleaned_h14, 2026-08: 45,932 rows; relative MAE 0.951
* cleaned_h14, 2026-09: 41,675 rows; relative MAE 0.970
* cleaned_h14, 2026-10: 10,142 rows; relative MAE 0.975
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
| h3 | cleaned | 531,316 | 0.943 | 0.791 |
| h3 | unfiltered | 531,316 | 0.944 | 0.791 |
| h7 | cleaned | 519,244 | 0.950 | 0.794 |
| h7 | unfiltered | 519,244 | 0.951 | 0.796 |
| h14 | cleaned | 496,298 | 0.956 | 0.794 |
| h14 | unfiltered | 496,298 | 0.956 | 0.795 |

## Dependence sensitivity (approximate; retrospective)

| Fit | Days | Block | Circular | Relative MAE 95% sensitivity interval |
|---|---:|---:|---|---|
| cleaned_next | 294 | 28 | True | [0.9466124704747211, 0.9553289376096209] |
| cleaned_next | 294 | 42 | True | [0.9465959787906589, 0.9553561558300662] |
| cleaned_next | 294 | 56 | True | [0.9468231598770885, 0.954935734070475] |
| cleaned_next | 294 | 28 | False | [0.9464652307156675, 0.9553814205024741] |
| cleaned_next | 294 | 42 | False | [0.946321796393453, 0.955007742337565] |
| cleaned_next | 294 | 56 | False | [0.9466117231550748, 0.9549846773100715] |

cleaned_next: HAC sensitivity = [{'bandwidth': 28, 'stat': -30.323685885496324, 'p_raw': 5.586879462309196e-202, 'p_holm8': 4.469503569847357e-201}, {'bandwidth': 42, 'stat': -34.81074292300273, 'p_raw': 1.672964646350862e-265, 'p_holm8': 1.3383717170806897e-264}, {'bandwidth': 56, 'stat': -39.36740762031415, 'p_raw': 0.0, 'p_holm8': 0.0}]; ACF = {'1': 0.12108340428494067, '7': 0.13299597944225738, '14': 0.0895405131362498, '28': 0.12196956788081044, '42': 0.18112571482241374, '56': 0.06586566439117982}; MASE exclusions = 24276; entity ratio quantiles = {'0.1': 0.8624873525896305, '0.25': 0.9152697309276653, '0.5': 0.9729091078113069, '0.75': 1.0417775390434492, '0.9': 1.1496320264454718}

| cleaned_h3 | 292 | 28 | True | [0.9395858782171079, 0.9475428943625884] |
| cleaned_h3 | 292 | 42 | True | [0.9396774428058322, 0.9472892048201847] |
| cleaned_h3 | 292 | 56 | True | [0.9399062971381117, 0.9469170535263003] |
| cleaned_h3 | 292 | 28 | False | [0.9391387794626431, 0.9472519351078891] |
| cleaned_h3 | 292 | 42 | False | [0.9391785891787708, 0.94711419214761] |
| cleaned_h3 | 292 | 56 | False | [0.9395427653797981, 0.9471581005489351] |

cleaned_h3: HAC sensitivity = [{'bandwidth': 28, 'stat': -27.53855555646793, 'p_raw': 6.067804063666031e-167, 'p_holm8': 4.2474628445662215e-166}, {'bandwidth': 42, 'stat': -27.28142410435867, 'p_raw': 7.046761704561708e-164, 'p_holm8': 4.932733193193196e-163}, {'bandwidth': 56, 'stat': -26.906487996736775, 'p_raw': 1.8440168657476154e-159, 'p_holm8': 1.1064101194485693e-158}]; ACF = {'1': 0.2015950739502468, '7': 0.19797443041149299, '14': 0.14925971923251063, '28': 0.15772839252679843, '42': 0.14334125172321172, '56': 0.09825705952962471}; MASE exclusions = 24008; entity ratio quantiles = {'0.1': 0.8433175060608677, '0.25': 0.8966249946350328, '0.5': 0.9559400358803292, '0.75': 1.0323217094374992, '0.9': 1.140156323572036}

| cleaned_h7 | 288 | 28 | True | [0.9456991065586228, 0.9534841660488945] |
| cleaned_h7 | 288 | 42 | True | [0.9460793392782851, 0.9534994306771272] |
| cleaned_h7 | 288 | 56 | True | [0.9464954662945408, 0.9530671322368975] |
| cleaned_h7 | 288 | 28 | False | [0.9456748481502891, 0.9538533005011347] |
| cleaned_h7 | 288 | 42 | False | [0.9457245521463067, 0.953341738613495] |
| cleaned_h7 | 288 | 56 | False | [0.9460016293978358, 0.952207888981713] |

cleaned_h7: HAC sensitivity = [{'bandwidth': 28, 'stat': -17.42667286245805, 'p_raw': 5.177194573265175e-68, 'p_holm8': 2.5885972866325874e-67}, {'bandwidth': 42, 'stat': -16.767591111585357, 'p_raw': 4.212431492801614e-63, 'p_holm8': 2.106215746400807e-62}, {'bandwidth': 56, 'stat': -16.69321312720227, 'p_raw': 1.4685022443334018e-62, 'p_holm8': 7.342511221667009e-62}]; ACF = {'1': 0.47251373865018115, '7': 0.32796375861576244, '14': 0.2103050456249888, '28': 0.1914580498497027, '42': 0.14624476647706866, '56': 0.2877339008675993}; MASE exclusions = 22739; entity ratio quantiles = {'0.1': 0.8486079585333598, '0.25': 0.8993206049342973, '0.5': 0.9552418590728006, '0.75': 1.0301133834172462, '0.9': 1.161741188281581}

| cleaned_h14 | 281 | 28 | True | [0.951717297808245, 0.96112245936314] |
| cleaned_h14 | 281 | 42 | True | [0.9525019233039089, 0.960756345118757] |
| cleaned_h14 | 281 | 56 | True | [0.9533540571399878, 0.9597090843392303] |
| cleaned_h14 | 281 | 28 | False | [0.9520960707882601, 0.9618829041778661] |
| cleaned_h14 | 281 | 42 | False | [0.9523022261903955, 0.9606081407300707] |
| cleaned_h14 | 281 | 56 | False | [0.9528954784121383, 0.958618804017531] |

cleaned_h14: HAC sensitivity = [{'bandwidth': 28, 'stat': -11.996743534075577, 'p_raw': 3.6955237857788266e-33, 'p_holm8': 7.391047571557653e-33}, {'bandwidth': 42, 'stat': -11.74930555029489, 'p_raw': 7.120157197759575e-32, 'p_holm8': 1.424031439551915e-31}, {'bandwidth': 56, 'stat': -11.716714972945164, 'p_raw': 1.0465185729636162e-31, 'p_holm8': 2.0930371459272325e-31}]; ACF = {'1': 0.6688613268863307, '7': 0.5476221996661275, '14': 0.1581485025937144, '28': 0.18234058961643343, '42': 0.18879816810905098, '56': 0.18985283978632905}; MASE exclusions = 22305; entity ratio quantiles = {'0.1': 0.8753590341449032, '0.25': 0.9165277949104109, '0.5': 0.9576364571169731, '0.75': 1.024099632910644, '0.9': 1.1548571550918867}

| unfiltered_next | 294 | 28 | True | [0.9454170473273844, 0.9553315592095426] |
| unfiltered_next | 294 | 42 | True | [0.9457138757133222, 0.9551666198586097] |
| unfiltered_next | 294 | 56 | True | [0.9459184845483785, 0.9547749238536561] |
| unfiltered_next | 294 | 28 | False | [0.9463874697815164, 0.9558966245694824] |
| unfiltered_next | 294 | 42 | False | [0.9462395531485931, 0.9552789643337903] |
| unfiltered_next | 294 | 56 | False | [0.9466507227418561, 0.9552718677046085] |

unfiltered_next: HAC sensitivity = [{'bandwidth': 28, 'stat': -23.08356966061217, 'p_raw': 6.771119370982455e-118, 'p_holm8': 4.062671622589473e-117}, {'bandwidth': 42, 'stat': -26.91546753763275, 'p_raw': 1.447684358018388e-159, 'p_holm8': 8.686106148110328e-159}, {'bandwidth': 56, 'stat': -28.74938403851801, 'p_raw': 9.219600335565678e-182, 'p_holm8': 6.453720234895974e-181}]; ACF = {'1': -0.036387496482463214, '7': -0.22730695324885297, '14': 0.05868619302210811, '28': 0.05672599571316569, '42': 0.11368457605351878, '56': 0.058691029722766644}; MASE exclusions = 24292; entity ratio quantiles = {'0.1': 0.8612454949757501, '0.25': 0.9135329039658546, '0.5': 0.9725467783228381, '0.75': 1.0410859243806079, '0.9': 1.1487634095230006}

| unfiltered_h3 | 292 | 28 | True | [0.9358161093642806, 0.9455665600799591] |
| unfiltered_h3 | 292 | 42 | True | [0.9360678510358603, 0.9451708656241321] |
| unfiltered_h3 | 292 | 56 | True | [0.9360059309484389, 0.9450352675694683] |
| unfiltered_h3 | 292 | 28 | False | [0.9379303994770232, 0.9463296503493686] |
| unfiltered_h3 | 292 | 42 | False | [0.9385407512048523, 0.9462008201115057] |
| unfiltered_h3 | 292 | 56 | False | [0.9388382760179976, 0.946143159084007] |

unfiltered_h3: HAC sensitivity = [{'bandwidth': 28, 'stat': -15.695551263682725, 'p_raw': 1.6222723404149016e-55, 'p_holm8': 6.4890893616596064e-55}, {'bandwidth': 42, 'stat': -15.452927871938106, 'p_raw': 7.209290236709586e-54, 'p_holm8': 2.8837160946838344e-53}, {'bandwidth': 56, 'stat': -15.033323217156646, 'p_raw': 4.4415294009332245e-51, 'p_holm8': 1.7766117603732898e-50}]; ACF = {'1': 0.3072588451466564, '7': 0.215260776187682, '14': 0.01541287683703918, '28': 0.10409882261033009, '42': 0.1013314789883447, '56': 0.15047525770445602}; MASE exclusions = 24024; entity ratio quantiles = {'0.1': 0.8426558487500334, '0.25': 0.8946881763313759, '0.5': 0.9535635838361625, '0.75': 1.0341103978285915, '0.9': 1.1474320243543468}

| unfiltered_h7 | 288 | 28 | True | [0.9457171033137054, 0.954123783207427] |
| unfiltered_h7 | 288 | 42 | True | [0.9460798599648615, 0.9544762496885733] |
| unfiltered_h7 | 288 | 56 | True | [0.9464485692755683, 0.9535316332677215] |
| unfiltered_h7 | 288 | 28 | False | [0.9463592945089857, 0.9550551162662942] |
| unfiltered_h7 | 288 | 42 | False | [0.946754161219266, 0.9548527078884897] |
| unfiltered_h7 | 288 | 56 | False | [0.9471723911028969, 0.9536448277690817] |

unfiltered_h7: HAC sensitivity = [{'bandwidth': 28, 'stat': -12.94825961309815, 'p_raw': 2.4034114742066285e-38, 'p_holm8': 7.210234422619885e-38}, {'bandwidth': 42, 'stat': -12.188125277823607, 'p_raw': 3.595987900150594e-34, 'p_holm8': 1.0787963700451782e-33}, {'bandwidth': 56, 'stat': -11.816015987401299, 'p_raw': 3.226249655468205e-32, 'p_holm8': 9.678748966404615e-32}]; ACF = {'1': 0.49895699883278943, '7': 0.3980466584316709, '14': 0.20331365995953823, '28': 0.19549448621372711, '42': 0.187185067182226, '56': 0.27838601116582623}; MASE exclusions = 22756; entity ratio quantiles = {'0.1': 0.8586572066006481, '0.25': 0.9060451393104805, '0.5': 0.95690893886703, '0.75': 1.0239812309283527, '0.9': 1.149494618734078}

| unfiltered_h14 | 281 | 28 | True | [0.9492553873725493, 0.9598526979546242] |
| unfiltered_h14 | 281 | 42 | True | [0.9504893574704855, 0.9594909750027337] |
| unfiltered_h14 | 281 | 56 | True | [0.9520286796509397, 0.9576977154140508] |
| unfiltered_h14 | 281 | 28 | False | [0.9512914496473905, 0.9610282650897801] |
| unfiltered_h14 | 281 | 42 | False | [0.9519465937347736, 0.959880370208151] |
| unfiltered_h14 | 281 | 56 | False | [0.9528660771996316, 0.957793231665322] |

unfiltered_h14: HAC sensitivity = [{'bandwidth': 28, 'stat': -11.090772618866493, 'p_raw': 1.3908128645445107e-28, 'p_holm8': 1.3908128645445107e-28}, {'bandwidth': 42, 'stat': -11.094824403241912, 'p_raw': 1.32920788499583e-28, 'p_holm8': 1.32920788499583e-28}, {'bandwidth': 56, 'stat': -11.182747273647538, 'p_raw': 4.9532464919618627e-29, 'p_holm8': 4.9532464919618627e-29}]; ACF = {'1': 0.6684391783617425, '7': 0.5383449931415876, '14': 0.12020711940437451, '28': 0.09642634797905612, '42': 0.150927426143038, '56': 0.1767112406894314}; MASE exclusions = 22321; entity ratio quantiles = {'0.1': 0.8759885051751953, '0.25': 0.9142844055467299, '0.5': 0.957582012108236, '0.75': 1.0233310400116584, '0.9': 1.1495562398171133}

State/commodity summaries and daily diagnostics are retained in manifest.json. Entity-resampling intervals do not establish independent-market inference.
