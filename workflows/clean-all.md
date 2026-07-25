---
description: Limpieza profunda de temporales, builds y artefactos de debug
---
// turbo-all
1. Elimina carpetas de build y archivos temporales de ejecución.
   - Command: .\gradlew.bat clean ; if (Test-Path "build/debug-artifacts") { Remove-Item -Recurse -Force "build/debug-artifacts" }
