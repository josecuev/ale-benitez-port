---
name: descubrimiento-sistemico-valor
description: Skill de descubrimiento sistémico COLABORATIVO humano-IA. Cuando facilitador describe NECESIDAD DE CLIENTE que requiere implementación, esta skill guía sesión de BRAINSTORMING donde AMBOS piensan JUNTOS iterativamente. IA hace preguntas estratégicas, abstrae complejidad en síntesis de 3-5 chunks (respeta límite cognitivo humano), profundiza bajo demanda, documenta automáticamente. OBJETIVO: Entender sistemicamente cómo problema ↔ necesidad ↔ contexto ↔ stakeholders ↔ expectativas ↔ tecnología se interrelacionan. SALIDA: Especificación MÍNIMA VIABLE de solución tecnológica + OPCIONALMENTE procedimientos asociados, LISTA PARA PASAR A EQUIPO DE IMPLEMENTACIÓN. NO es documento teórico. Es blueprint ejecutable que equipo técnico usa para construir. Máximo 5 rondas. Agnóstico de dominio. Después: equipo implementa + valida si problema se resolvió.
compatibility: Brainstorming colaborativo, pensamiento sistémico, design thinking, facilitación de descubrimiento, agnóstico de dominio, salida orientada a implementación inmediata
---

# SKILL: Descubrimiento Sistémico de Valor (Humano + IA)

**Core Philosophy**: 
- ❌ NO: "Aquí hay un problema, proponemos esta solución"
- ✅ SÍ: "Aquí hay una necesidad → JUNTOS (humano + IA) entendemos sistémicamente → EMERGE especificación ejecutable"

**Resultado Final**: 
- ✅ Especificación mínima viable de solución tecnológica
- ✅ Opcionalmente: Procedimientos de implementación asociados
- ✅ LISTO PARA: Equipo técnico comience a construir/implementar

**Después de Skill**: Equipo implementa + Valida en campo si problema se resolvió (feedback loop)

---

## TRIGGER: Cuándo se Activa

**Facilitador describe**: "El cliente necesita [OUTCOME] porque [RAZÓN]. Hay que implementarlo."

```
PATRÓN DE TRIGGER:
"El cliente necesita [qué] 
porque [razón comercial/operacional]
y debe implementarse [restricción de tiempo/budget/contexto]"

EJEMPLOS REALES:

1. Transporte:
"Operadores necesitan validar cumplimiento en minutos (no 4 horas)
porque decisiones tardan 2 semanas y buses incumplen regulación.
Debe implementarse en 12 semanas, presupuesto $50k"

2. Healthcare:
"Pacientes necesitan ver historial médico en tiempo real
porque ahora consultan y 24hrs después reciben info, pierden contexto.
Clínicas exigen que sea HIPAA-compliant y de bajo costo"

3. Finanzas:
"Sistema de pagos debe procesar 10x más transacciones sin latencia
porque Black Friday genera picos y se cae el sistema.
Necesitamos mantener SLA 99.9% con presupuesto actual"

4. Datos:
"Analistas necesitan acceso unificado a datos (hoy están en 5 sistemas)
porque pierden 8 horas/semana buscando datos, no analizan.
IT quiere reducir deuda técnica de integraciones manuales"

CARACTERÍSTICA COMÚN: Necesidad + Razón + Restricción
```

---

## ESTRUCTURA: Espiral Colaborativo (Máximo 5 Rondas)

```
┌─────────────────────────────────────────────────────────┐
│  SESIÓN BRAINSTORMING: Facilitador (Humano) + IA        │
│                                                         │
│  RONDA 1: Contexto Inicial → Síntesis                  │
│  RONDA 2: Necesidad + Stakeholders → Síntesis          │
│  RONDA 3: Contexto Sistémico → Síntesis                │
│  RONDA 4: Oportunidades Tecnológicas → Síntesis        │
│  RONDA N: Iterar hasta CONVERGENCIA                    │
│                                                         │
│  CONVERGENCIA: Ambos (facilitador + IA) dicen          │
│  "Entendemos el sistema completo"                      │
│                                                         │
│  → IA genera ESPECIFICACIÓN MÍNIMA VIABLE              │
│  → Listo para Equipo de Implementación                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## PRINCIPIOS CLAVE

### 1. Colaboración Real Humano-IA (No Asesor Unilateral)

```
❌ INCORRECTO:
IA: "¿Problema?"
Facilitador: "Validación manual"
IA: "Necesitamos ML" → Facilitador acepta pasivamente

✅ CORRECTO (Brainstorming):
IA: "¿Cuál es exactamente el problema?"
Facilitador: "Validación manual, 4 horas/día"
IA: "¿Solo validación o hay otras tareas en esas 4 horas?"
Facilitador: "Ah, también cargan datos en 3 sistemas..."
IA: "Entonces: validación LENTA + duplicación de entrada"
Facilitador: "Exacto. Pero regulador exige que esté en sistema principal"
IA: "Entonces problema real es: integración + validación"
        ↓
Ambos refinaron JUNTOS el entendimiento
```

### 2. Abstracción Progresiva (3-5 Chunks Máximo)

Humano procesa máximo 3-5 piezas simultáneamente.
**IA maneja complejidad internamente**, muestra solo síntesis.

```
IA (internamente): Analiza 20+ dimensiones
IA (respuesta): Resume 3-5 puntos clave máximo

Ejemplo:
Facilitador: "Regulador, operadores, supervisores, auditor, CEO"

IA (internamente): Mapea roles, permisos, responsabilidades, 
conflictos de expectativas, leyes, presupuestos...

IA (respuesta):
"5 stakeholders con 2 expectativas cada uno = 10 expectativas.
Pero se agrupan en 4 categorías:
  1. VELOCIDAD (operador, supervisor)
  2. TRAZABILIDAD (auditor, regulador)
  3. PRECISIÓN (todos)
  4. ROI (CEO)

¿Correcto?"
```

### 3. Documentación Viva en Paralelo

Facilitador **NO** documenta → IA lo hace automáticamente.

```
Lo que FACILITADOR ve:
├─ Síntesis de 3-5 puntos
├─ Pregunta estratégica siguiente
└─ Opción para profundizar ("¿Quieres más de X?")

Lo que IA DOCUMENTA (invisible):
├─ User stories emergentes
├─ Relaciones sistémicas
├─ Stakeholders + expectativas
├─ Obstáculos + oportunidades
├─ Soluciones tecnológicas candidatas
├─ Cambios procedimentales necesarios
└─ Paquete de valor actualizado c/ronda
```

### 4. Agnóstico de Dominio

Mismo flujo para:
- Transporte, Healthcare, Finanzas, Datos, Educación, Retail...
- Solo cambia contexto, estructura es idéntica

### 5. Máximo 5 Rondas (Pragmatismo)

- 1-2 rondas: Problemas simples
- 3-4 rondas: Complejos
- 5 rondas: Muy complejos

Si >5 rondas: Escalara (necesita más research, stakeholder meetings, etc.)

---

## ANATONOMÍA DE CADA RONDA

### PASO A: IA Hace Pregunta Estratégica

Pregunta explora dimensión sistémica no-entendida aún.

```
RONDA 1 - Problema:
├─ "¿Cuál es el problema ESPECÍFICO?"
├─ "¿Cuál es el impacto (tiempo, costo, riesgo)?"
├─ "¿A quién afecta?"
└─ "¿Cuál es la causa raíz?"

RONDA 2 - Necesidad + Stakeholders:
├─ "¿Qué espera REALMENTE el cliente?"
├─ "¿Hay otros stakeholders?"
├─ "¿Qué espera cada uno?"
└─ "¿Hay conflictos de expectativas?"

RONDA 3 - Contexto Sistémico:
├─ "¿Qué sistemas/datos/procesos ya existen?"
├─ "¿Qué AYUDA a resolver?"
├─ "¿Qué OBSTACULIZA?"
└─ "¿Hay restricciones (legales, técnicas, presupuestarias)?"

RONDA 4 - Oportunidades Tecnológicas:
├─ "¿Dónde suma tecnología (IA, cloud, datos, automatización)?"
├─ "¿Sin tecnología, cuál es el costo?"
├─ "¿Hay restricciones técnicas?"
└─ "¿MUST vs NICE-TO-HAVE?"

RONDA 5+ - Convergencia:
├─ "¿Todas las perspectivas cubiertas?"
├─ "¿Hay gaps sistémicos?"
└─ "¿Paquete de valor claro?"
```

### PASO B: Facilitador Responde + Da Contexto

Vos respondés + das contexto ESPONTÁNEO que creas necesario.

```
IA: "¿A quién afecta?"
Facilitador: "A operadores principalmente, pierden 4 horas/día.
Pero también supervisor que no ve qué pasa.
Y regulador sin trazabilidad...
Ah, y team de datos que quería hacer ML pero datos están dispersos."

→ En UNA respuesta, diste perspectiva de 4 stakeholders + oportunidad.
```

### PASO C: IA Resume en 3-5 Síntesis

IA abstrae, devuelve síntesis MÁXIMO de 3-5 puntos.

```
IA: "Entonces 4 perspectivas:
  1. Operadores: Tiempo (4 horas/día)
  2. Supervisor: Visibilidad falta
  3. Regulador: Trazabilidad falta
  4. Data team: Datos dispersos (oportunidad)

¿Es completo? ¿Falta alguien?"

Facilitador: "CEO también quiere ROI rápido"
IA: "Anotado. 5 stakeholders + 1 restricción de ROI.
¿Pasamos a entender qué espera cada uno?"
```

### PASO D: Facilitador Pide Profundidad (Bajo Demanda)

```
Facilitador: "¿Profundiza qué significa 'datos dispersos'?"
IA: [Ahora sí da detalles, porque facilitador lo pidió]

Facilitador: "¿Cómo mitigamos riesgo de baja adopción?"
IA: [Explora opciones]
```

---

## RONDAS DETALLADAS

### RONDA 1: Problema + Contexto Inicial

**Objetivo**: Entender QUÉ es lo que cliente necesita + CUÁL es el problema hoy.

```
IA: "Me dijiste que [necesidad]. Para entender bien,
¿cuál es el problema ESPECÍFICO hoy?"

Facilitador: [Describe problema específico]

IA: "Entonces:
  1. Problema: [síntesis]
  2. Impactado: [quiénes, cuántos]
  3. Impacto: [métrica si hay]
  4. Causa raíz (supuesta): [hipótesis]
  5. ¿Agregamos algo?"

Facilitador: [Ajusta si necesario]

IA Pregunta Siguiente: "¿Hay otros stakeholders además de [X, Y]?"

SALIDA RONDA 1:
✓ Problema entendido (no confundido con síntomas)
✓ Impacto cuantificado
✓ Stakeholders primarios identificados
```

---

### RONDA 2: Necesidad + Expectativas

**Objetivo**: Entender QUÉ ESPERA realmente cada stakeholder (resultado, no solución).

```
IA: "Para [Stakeholder 1], ¿cuál es el RESULTADO que espera?
No solución (ej: no 'ML model'), sino qué debería pasar?"

Facilitador: "Debería poder validar en minutos, no 4 horas"

IA: "¿Otras expectativas? ¿Explicabilidad? ¿Confiabilidad?"

Facilitador: "Sí, entender por qué. Y auditable quién decidió"

IA: "Entonces [Stakeholder 1] espera:
  1. Tiempo: Minutos (vs 4 horas)
  2. Explicabilidad: Entender por qué
  3. Auditabilidad: Quién decidió qué
  ¿Correcto?"

Facilitador: "Sí, esos 3"

IA: "¿Y para [Stakeholder 2]?" [Repite para cada uno]

SALIDA RONDA 2:
✓ Expectativas de TODOS (3-5 stakeholders) documentadas
✓ Conflictos de expectativas identificados (si hay)
✓ Prioridades relativas claras
```

---

### RONDA 3: Contexto Sistémico

**Objetivo**: Entender cómo esta necesidad se relaciona con REST del sistema.

```
IA: "¿Qué sistemas, procesos, datos ya existen para esto?
Ej: ¿GPS? ¿Base datos? ¿Regulaciones? ¿Integraciones?"

Facilitador: "GPS existe pero 2% falla. DB es legacy.
Regulación Res. 65 en Word. Sistema de multas aislado.
Cloud disponible."

IA: "Entonces contexto sistémico:
  1. GPS: Existe, 98% cobertura (riesgo 2%)
  2. DB: Legacy, consistencia problemas
  3. Regulación: Clara pero no estructurada
  4. Sistema multas: Aislado (obstáculo)
  5. Cloud: Disponible (ayuda)"

IA Pregunta: "De esto, ¿QUÉ AYUDA a resolver?
¿QUÉ OBSTACULIZA?"

SALIDA RONDA 3:
✓ Contexto sistémico mapeado
✓ Ayudas + Obstáculos claros
✓ Dependencias documentadas
```

---

### RONDA 4: Oportunidades Tecnológicas

**Objetivo**: Explorar DÓNDE tecnología suma valor (sin imponer solución).

```
IA: "Mirando:
  - Problema: [síntesis R1]
  - Necesidad: [síntesis R2]
  - Contexto: [síntesis R3]

¿Dónde TECNOLOGÍA (IA, cloud, datos, automatización) 
reduce tiempo/costo/error?"

Facilitador: "Validación manual → ML model
Dashboard para supervisión
Agent que explique decisión"

IA: "Entonces oportunidades:
  1. ML para validación (reduce manual)
  2. Dashboard realtime (da visibilidad)
  3. Agent explicativo (mejora confianza)
  4. Integración multas (amplía valor)
  5. ¿Hay más?"

IA Pregunta: "Sin estas, ¿cuál es el costo?
¿Es viable sin tech?"

SALIDA RONDA 4:
✓ Oportunidades tecnológicas claras (3-5 candidatas)
✓ Impact estimado de cada una
✓ Viabilidad inicial (con vs sin tech)
✓ Trade-offs documentados
```

---

### RONDA 5+: Convergencia + Validación

**Objetivo**: Confirmar que AMBOS (facilitador + IA) entendemos sistema completo.

```
IA: "Validemos convergencia. Hemos identificado:

PROBLEMA:
  [síntesis ejecutiva]

NECESIDAD (por stakeholder):
  [síntesis ejecutiva]

CONTEXTO SISTÉMICO:
  [síntesis ejecutiva]

OPORTUNIDADES TECNOLÓGICAS:
  [síntesis ejecutiva]

PAQUETE DE VALOR (qué cambiaremos):
  [síntesis ejecutiva]

¿Es completo? ¿Falta algo sistémico?"

Facilitador: "Me preocupa adopción de usuarios"

IA: "Riesgo importante. ¿Afecta paquete de valor?"

Facilitador: "Sí, necesitamos capacitación + change management"

IA: "Agregado. Entonces paquete final:
  1. Validación automática (ML)
  2. Dashboard realtime
  3. Agent explicativo
  4. Integración con multas
  5. Capacitación + Change management

¿Esto es definitivo?"

Facilitador: "Sí"

IA: "✅ CONVERGENCIA. Generamos especificación para implementación"

SALIDA RONDA 5:
✓ CONVERGENCIA confirmada (ambos entienden)
✓ Paquete de valor final + COMPLETO
✓ LISTO PARA: Especificación de implementación
```

---

## SALIDA FINAL: ESPECIFICACIÓN MÍNIMA VIABLE (EMV)

Cuando convergemos, IA genera:

```
═══════════════════════════════════════════════════════════
ESPECIFICACIÓN MÍNIMA VIABLE PARA IMPLEMENTACIÓN
═══════════════════════════════════════════════════════════

PROYECTO: [Nombre]
FECHA: [Fecha]
RONDAS CONVERGENCIA: [N]
FACILITADOR: [Nombre]

───────────────────────────────────────────────────────────
1. PROBLEMA IDENTIFICADO
───────────────────────────────────────────────────────────
Síntesis ejecutiva de:
├─ Qué está fallando hoy (específico, no síntoma)
├─ Quién se ve afectado (stakeholders)
├─ Impacto cuantificado (tiempo, costo, riesgo)
└─ Causa raíz (no síntoma)

Ejemplo:
"Operadores validan cumplimiento manualmente (4 hrs/día),
generando 15% de errores y decisiones que tardan 2 semanas.
Afecta: Operadores (sobrecarga), Supervisor (sin visibilidad),
Regulador (riesgo compliance). Causa: Proceso manual sin herramientas"

───────────────────────────────────────────────────────────
2. NECESIDAD + EXPECTATIVAS (POR STAKEHOLDER)
───────────────────────────────────────────────────────────
Stakeholder | Expectativa Primaria | Expectativa Secundaria
─────────────────────────────────────────────────────────
Operador    | Validación < 5min   | Explicable, confiable
Supervisor  | Dashboard realtime  | Alertas automáticas
Regulador   | Trazabilidad        | Auditable
CEO         | ROI rápido          | Escalabilidad

Conflictos identificados (si hay):
[Listar con resolución propuesta]

───────────────────────────────────────────────────────────
3. CONTEXTO SISTÉMICO
───────────────────────────────────────────────────────────
QUÉ AYUDA:
├─ GPS realtime (entrada de datos)
├─ Cloud infraestructura
└─ Regulación clara (Res. 65)

QUÉ OBSTACULIZA:
├─ DB legacy (inconsistencia)
├─ Sistema de multas aislado (no integrado)
└─ Conocimiento operadores bajo (Res. 65)

DEPENDENCIAS CRÍTICAS:
├─ GPS data 98%+ cobertura (asumido)
├─ DB cleanup para consistencia
└─ Capacitación operadores

───────────────────────────────────────────────────────────
4. SOLUCIÓN TECNOLÓGICA (ESPECIFICACIÓN MÍNIMA)
───────────────────────────────────────────────────────────

COMPONENTE 1: Validador Automático
├─ Qué es: Sistema que valida cumplimiento Res. 65 automáticamente
├─ Tecnología: ML model (entrenado con datos históricos)
├─ Entrada: Evento GPS en realtime
├─ Salida: Decisión (cumple/no cumple) + confianza %
├─ Latencia: < 30 segundos
├─ Precisión objetivo: >= 99%
└─ Interfaz: [Brevemente qué ve operador]

COMPONENTE 2: Dashboard Realtime
├─ Qué es: Visualización estado cumplimiento por bus + flota
├─ Para quién: Supervisores
├─ Datos clave: % cumplimiento por bus, alertas, histórico
├─ Latencia: < 2 segundos
└─ Disponible: Web + Mobile

COMPONENTE 3: Agent Explicativo
├─ Qué es: Explica en lenguaje natural por qué validador dijo "no cumple"
├─ Tecnología: LLM + RAG (referencias a Res. 65)
├─ Entrada: Decisión de validador + evento GPS + contexto
├─ Salida: Explicación clara ("Incumple porque salió de zona permitida")
└─ Auditable: Sí (logs de explicación)

COMPONENTE 4: Integración Sistema Multas
├─ Qué es: Conecta decisión de validador con aplicación de multa
├─ Flujo: Validador detecta incumplimiento → automáticamente inicia proceso multa
├─ Cambio: Acoplamiento antes (manual) → ahora (automático)
└─ Restricción: Requiere acuerdo legal/procedimiento nuevo

───────────────────────────────────────────────────────────
5. CAMBIOS PROCEDIMENTALES (OPCIONAL)
───────────────────────────────────────────────────────────

CAMBIO 1: Flujo de Validación
├─ Antes: Operador valida manual → Supervisor revisa → Decision
├─ Ahora: Sistema valida automático → Si duda, operador confirma
└─ Impacto: -3.5 hrs/día, +confianza si es explicable

CAMBIO 2: Capacitación Operadores
├─ Qué: Operadores aprenden a:
│  └─ Interpretar explicación del Agent
│  └─ Actuar en casos excepcionales
│  └─ Confiar en validador
├─ Duración: 1 semana
└─ Crítico para: Adopción

CAMBIO 3: Flujo de Escalada
├─ Si validador es uncertain (confianza < 80%):
│  └─ Alert a operador para confirmar
│  └─ Si ambiguo: Envía a supervisor
├─ Asegura: No hay decisiones incorrectas sin revisión

───────────────────────────────────────────────────────────
6. PAQUETE DE VALOR (RESUMEN PARA CLIENTE)
───────────────────────────────────────────────────────────

QUÉ CAMBIAREMOS:
└─ Validación manual (4 hrs/día, 15% errores) → 
   Automática (< 5 min, 99% precisión)

VALOR ESPERADO:
├─ Operadores: -3.5 hrs/día (pueden hacer otra cosa)
├─ Decisiones: 10x más rápidas (2 sem → 2 días)
├─ Precisión: +99% (vs 85% manual)
├─ Escalabilidad: De 50 a 5000 buses sin costo manual
├─ Cumplimiento: Regulación Res. 65 garantizada
└─ ROI: Se paga en [X meses] con ahorros operativos

RIESGOS + MITIGACIÓN:
├─ Baja adopción → Capacitación + Agent explicativo
├─ Integración multas compleja → Roadmap MVP+1
└─ Escalabilidad insuficiente → Cloud elástica + load testing

───────────────────────────────────────────────────────────
7. PRÓXIMOS PASOS: IMPLEMENTACIÓN
───────────────────────────────────────────────────────────

ENTREGA A: Equipo Técnico (Dev, QA, DevOps)

PARA QUE: Construyan/implementen componentes 1-4

ROADMAP SUGERIDO:
├─ Sprint 1 (4 sem): Validador automático + MVP de Dashboard
├─ Sprint 2 (3 sem): Agent explicativo + integración básica multas
├─ Sprint 3 (2 sem): Capacitación + validación en campo
└─ Sprint 4: Escalabilidad a 5000 buses + optimizaciones

CRITERIO DE ÉXITO (POST-IMPLEMENTACIÓN):
├─ ¿Operadores validan en < 5 minutos? → SÍ ✓
├─ ¿Precisión >= 99%? → SÍ ✓
├─ ¿Supervisor ve realtime? → SÍ ✓
├─ ¿Auditor puede trazabilidad? → SÍ ✓
├─ ¿Adopción operadores >= 80%? → SÍ ✓
└─ Si TODO SÍ: Problema resuelto ✓

───────────────────────────────────────────────────────────
8. APRENDIZAJES DEL DESCUBRIMIENTO
───────────────────────────────────────────────────────────

Qué descubrimos (no era obvio):
├─ Integración multas es CRÍTICA, no nice-to-have
├─ Explicabilidad es KEY para adopción (no es técnico)
└─ Escalabilidad requiere cambio de infraestructura

Qué confirmamos:
├─ Problema es real y cuantificado
├─ Tecnología suma valor significativo
└─ Todos los stakeholders alineados

Qué preguntas quedaron abiertas:
├─ ¿Exactamente cómo integramos con multas? (para Sprint 2)
├─ ¿Nivel de automatización vs confirmación humana? (User testing)
└─ [Otras]

═══════════════════════════════════════════════════════════
```

## ROL DEL FACILITADOR EN FASES 2 Y 3

**Después que esta skill genera EMV, facilitador**:

```
FASE 2: CONSTRUCCIÓN

├─ Lee EMV → Entiende qué se va a construir
│
├─ Coordina con equipo técnico:
│  ├─ Selecciona skills del catálogo apropiadas
│  ├─ Crea brief claro (EMV sirve de brief)
│  ├─ Hace seguimiento de progreso
│  └─ Resuelve bloqueos/dudas técnicas
│
├─ Cuando código está listo:
│  └─ Equipo ejecuta tests automatizados:
│     ├─ Unit tests (componentes aisladas)
│     ├─ Integration tests (componentes juntas)
│     ├─ E2E tests (flujo completo)
│     ├─ Load testing (escalabilidad)
│     ├─ Security testing (si aplica)
│     └─ Cuando TODO PASA: "Listo para validación"
│
└─ Preparación para Fase 3:
   ├─ Setup ambiente: Staging realista
   ├─ Convoca usuarios/stakeholders para validar
   ├─ Prepara métricas de validación
   └─ Define criterios de go/no-go

FASE 3: VALIDACIÓN (Con Facilitador)

├─ Facilitador VALIDA EN CAMPO:
│  ├─ Operadores usan el sistema:
│  │  ├─ ¿Pueden validar en < 5 minutos? (SÍ/NO)
│  │  ├─ ¿Entienden explicaciones del Agent? (SÍ/NO)
│  │  ├─ ¿Confían en validador? (SÍ/NO)
│  │  └─ ¿Lo usarían en producción? (SÍ/NO)
│  │
│  ├─ Supervisores usan dashboard:
│  │  ├─ ¿Ven estado realtime? (SÍ/NO)
│  │  ├─ ¿Es intuitivo? (SÍ/NO)
│  │  └─ ¿Toman mejores decisiones? (SÍ/NO)
│  │
│  ├─ Auditor verifica:
│  │  ├─ ¿Hay trazabilidad completa? (SÍ/NO)
│  │  ├─ ¿Es auditable? (SÍ/NO)
│  │  └─ ¿Cumple regulaciones? (SÍ/NO)
│  │
│  └─ PREGUNTA CRÍTICA:
│     ¿El PROBLEMA ORIGINAL está resuelto?
│     ├─ Antes: Validación manual 4 hrs/día, 15% errores
│     ├─ Después: Validación < 5 min, 99% precisión
│     └─ ¿SÍ RESUELTO o NO?
│
├─ RESULTADO DE VALIDACIÓN:
│  ├─ ✅ SÍ a todo → SOLUCIÓN VÁLIDA Y LISTA
│  │  ├─ Deploy a producción
│  │  ├─ Capacitación en vivo
│  │  └─ Go-live
│  │
│  └─ ⚠️ NO a algo → FEEDBACK LOOP
│     ├─ Facilitador identifica QUÉ no funciona
│     ├─ Documenta: Problema + Causa probable
│     ├─ Comunica a equipo técnico
│     ├─ Decisión: ¿Vuelve a Fase 2 (ajustes) o vuelve a Descubrimiento?
│     │  (Si es cambio sistémico) → Vuelve a esta skill
│     │  (Si es bug/ajuste técnico) → Vuelve a Fase 2
│     └─ Iteración hasta que TODO pase

CRITERIO DE EXITO TOTAL:
├─ ✅ Problema original RESUELTO (métricas)
├─ ✅ Stakeholders SATISFECHOS (expectativas cubiertas)
├─ ✅ Sistema ESTABLE (tests pasan, cero errores críticos)
├─ ✅ Usuarios ADOPTAN (capacitación completa)
└─ ✅ ROI VISIBLE (o timing claro para verlo)
```

**Flujo de Comunicación**:
```
FACILITADOR ↔ EQUIPO TÉCNICO (Fase 2)
├─ Facilitador: EMV clara, responde dudas
├─ Equipo: Reporta progreso, bloqueos
└─ Comunicación: Semanal (o según cadencia)

FACILITADOR ↔ STAKEHOLDERS (Fase 3)
├─ Facilitador: Convoca, facilita pruebas, recolecta feedback
├─ Stakeholders: Usan sistema, dan feedback
└─ Comunicación: Tests en vivo, notas, métricas
```

---

---

## DESPUÉS: FASES 2 Y 3 (Fuera de Esta Skill)

```
FLUJO POST-DESCUBRIMIENTO:

┌─────────────────────────────────────────────────────┐
│  SALIDA SKILL ACTUAL (EMV)                          │
│  Especificación Mínima Viable + Cambios Procedimentales
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│  FASE 2: CONSTRUCCIÓN (Usando Otras Skills)         │
│                                                     │
│  EMV describe QUÉ construir                         │
│  Otras skills del catálogo CONSTRUYEN:              │
│                                                     │
│  ├─ Skill: Desarrollo Frontend → UI del Dashboard  │
│  ├─ Skill: Backend API → Validador automático      │
│  ├─ Skill: ML/Data → Modelo de validación          │
│  ├─ Skill: Integración → Conexión con multas       │
│  ├─ Skill: DevOps → Infrastructure como código     │
│  ├─ Skill: Documentación → Procedimientos cambio   │
│  └─ Skill: Capacitación → Entrenamientos usuarios  │
│                                                     │
│  Cuando CÓDIGO está listo:                          │
│  ├─ Tests automatizados (unit, integration, E2E)   │
│  ├─ Verificaciones QA (funcionales, no-func)       │
│  ├─ Load testing (escalabilidad)                   │
│  ├─ Security testing (si aplica)                   │
│  └─ Cuando TODO PASA: Solución lista para validar  │
│                                                     │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────────┐
│  FASE 3: VALIDACIÓN (Con Facilitador Humano)        │
│                                                     │
│  Facilitador valida EN CAMPO:                       │
│  ├─ ¿Operadores pueden validar en < 5 min?         │
│  │  └─ Métrica: Tiempo real vs expected             │
│  │                                                 │
│  ├─ ¿Precisión >= 99%?                             │
│  │  └─ Métrica: Confusion matrix vs gold standard  │
│  │                                                 │
│  ├─ ¿Supervisor ve realtime + entiende datos?      │
│  │  └─ Métrica: Usabilidad, feedback usuario       │
│  │                                                 │
│  ├─ ¿Explicaciones del Agent son útiles?           │
│  │  └─ Métrica: % de veces que operador confía     │
│  │                                                 │
│  ├─ ¿Cambios procedimentales funcionan?            │
│  │  └─ Métrica: Adopción, resistencia, resultados │
│  │                                                 │
│  ├─ ¿Problema ORIGINAL ESTÁ RESUELTO?              │
│  │  └─ Métrica: Impacto inicial (4hrs → X min)    │
│  │                                                 │
│  RESULTADO VALIDACIÓN:                             │
│  ├─ SÍ a TODO → ✅ SOLUCIÓN VÁLIDA, LISTA          │
│  │                                                 │
│  └─ NO a alguno → ⚠️ FEEDBACK LOOP                 │
│     ├─ Qué no funcionó                             │
│     ├─ Por qué (facilitador + equipo investiga)   │
│     ├─ Ajustes necesarios (Sprint N+1)             │
│     └─ Vuelve a Fase 2 (re-construir) o Fase 3    │
│        (validación nuevamente)                     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**IMPORTANTE**: Esta skill TERMINA cuando EMV está listo.
Las Fases 2 y 3 son RESPONSABILIDAD del facilitador + equipo técnico.
Si validación falla → Feedback loop (puede necesitar volver a esta skill).

---

## ENTRADA A FASE 2: Cómo Usa Otras Skills

**EMV describe COMPONENTES**:
```
COMPONENTE 1: Validador Automático
├─ Qué es: ML model que valida Res. 65
├─ Entrada: GPS event realtime
├─ Salida: cumple/no-cumple + confianza %
└─ Latencia: < 30s

COMPONENTE 2: Dashboard Realtime
├─ Qué es: Visualización para supervisores
├─ Datos: % cumplimiento por bus
└─ Tech: Web + Mobile
```

**Equipo técnico TRADUCE a requisitos**:
```
Para COMPONENTE 1 (ML Validator):
├─ Usa Skill: "ML Model Training & Deployment"
│  ├─ Input: Datos históricos validados
│  ├─ Output: Modelo .pkl con precisión >= 99%
│  └─ Integración: REST API endpoint
│
├─ Usa Skill: "Backend API Development"
│  ├─ Construye: /validate endpoint
│  ├─ Input: GPS event JSON
│  └─ Output: {decision, confidence, timestamp}
│
└─ Usa Skill: "DevOps / Infrastructure"
   ├─ Deploy: En cloud
   ├─ Escalabilidad: Auto-scaling a 5k events/sec
   └─ Monitoreo: Métricas, alertas

Para COMPONENTE 2 (Dashboard):
├─ Usa Skill: "Frontend Development"
│  ├─ UI: React / Vue / similar
│  ├─ Data binding: Realtime (WebSocket)
│  └─ Responsive: Mobile + desktop
│
└─ Usa Skill: "Data Visualization"
   ├─ Gráficos: Barras, mapas, alertas
   └─ UX: Intuitivo para supervisores
```

Entonces:
- **Esta skill** define CUÁL es el problema + QUÉ construir + POR QUÉ
- **Otras skills** saben CÓMO construirlo (técnicas específicas)

---

## COMPARACIÓN: Skill Anterior vs Esta

| Aspecto | Skill Anterior | Esta Skill |
|---------|----------------|-----------|
| Salida | Documento teórico | **Especificación Mínima Viable ejecutable** |
| Documentación | Manual, al final | **Automática, en paralelo** |
| Complejidad que ve facilitador | Toda (abrumador) | **3-5 síntesis (procesable)** |
| Iteración | Hasta 10+ rondas | **Máximo 5 (pragmático)** |
| Profundidad | Fija | **Bajo demanda (pide si quiere)** |
| Próximo paso | "Ahora diseñamos" | **"Equipo, empiecen a construir"** |
| Feedback post-implementación | No contemplado | **¿Problema resuelto SÍ/NO? → Loop** |

---

## TIPS PARA USAR BIEN ESTA SKILL

1. **Sé honesto**: Si no sabes algo, dilo. IA trabaja con "desconocido"
2. **Contexto espontáneo**: Mientras respondo, si se te ocurre algo, mencionalo
3. **Cuestiona síntesis**: Si resumen no es exacto, corregí
4. **Pide profundidad**: Cuando necesites más detalle
5. **No te preocupes por estructura**: IA documenta en paralelo
6. **Piensa en voz alta**: Es brainstorming, no es entrevista formal

---

## Trigger para Activar Esta Skill (Cómo Usarla)

Simplemente escribí algo como:

```
"Cliente necesita X porque Y. Hay que implementarlo.
¿Cómo exploramos esto sistemicamente?"

O:

"Nuestros operadores tardan 4 horas validando cumplimiento.
Necesitamos automatizar. ¿Empezamos a explorar?"

O:

"Regulador exige auditoría completa pero hoy es manual.
Necesitamos una solución. ¿Descubrimos juntos?"
```

Y yo activo la skill automáticamente 🚀

