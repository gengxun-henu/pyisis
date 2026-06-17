# pyisis Windows Build and Test

These scripts configure, build, and test pyisis against a Windows-native
`ISIS_PREFIX`.

Set `ISIS_PREFIX` before running the scripts:

```powershell
$env:ISIS_PREFIX = "$PWD\build\windows\isis-prefix"
```

The scripts set `PYTHONPATH`, `ISISDATA`, and `PATH` so Python can find the
built pyisis package and Windows can find ISIS/Qt runtime DLLs.
