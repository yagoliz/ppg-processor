# PPG Processing

Simple GUI to process PPG data coming from Polar VeritySense sensors. The expected input format are CSV files with the following structure:

```csv
499,270445,314778,266630,1042
0,270102,314364,266328,1023
0,269850,313994,266047,1057
0,269660,313655,265763,1102
0,269407,313279,265615,1119
0,269357,313093,265575,1057
0,269394,313184,265681,1079
```

where the columns should have `delta/timestamp, P0, P1, P2, AMBIENT`.