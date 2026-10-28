import { describe, expect, it } from "vitest"

import { importSource } from "./import"
import { layoutProgram } from "./layout"
import { guessingGame, toSource } from "./model"

const AREA = `Algoritmo AreaTriangulo
    Definir base, altura, area Como Real;
    Escribir "Ingrese la base:";
    Leer base;
    Escribir "Ingrese la altura:";
    Leer altura;
    area <- (base * altura) / 2;
    Escribir "El area es ", area;
FinAlgoritmo
`

const MAYOR = `Algoritmo Mayor
    Definir a, b Como Entero;
    Leer a;
    Leer b;
    Si a > b Entonces
        Escribir a;
    Sino
        Si a = b Entonces
            Escribir "iguales";
        Sino
            Escribir b;
        FinSi
    FinSi
FinAlgoritmo
`

const TABLA = `Algoritmo Tabla
    Definir n, i, producto Como Entero;
    Leer n;
    Para i <- 1 Hasta 10 Hacer
        producto <- n * i;
        Escribir n, " x ", i, " = ", producto;
    FinPara
FinAlgoritmo
`

const PROMEDIO = `Algoritmo Promedio
    Definir nota, suma, promedio Como Real;
    Definir cantidad, i Como Entero;
    Leer cantidad;
    suma <- 0;
    Si cantidad > 0 Entonces
        Para i <- 1 Hasta cantidad Hacer
            Leer nota;
            suma <- suma + nota;
        FinPara
        promedio <- suma / cantidad;
        Escribir promedio;
    Sino
        Escribir "sin notas";
    FinSi
FinAlgoritmo
`

const ARREGLO = `Algoritmo Arreglo
    Definir numeros, i, suma Como Entero;
    Dimension numeros[5] Como Entero;
    suma <- 0;
    Para i <- 1 Hasta 5 Hacer
        numeros[i] <- i * 10;
        suma <- suma + numeros[i];
    FinPara
    Escribir suma;
FinAlgoritmo
`

const DOBLAR = `Funcion resultado <- Doblar(n)
    Definir resultado, n Como Entero;
    resultado <- n * 2;
FinFuncion
Algoritmo Doble
    Definir numero Como Entero;
    Leer numero;
    Escribir Doblar(numero);
FinAlgoritmo
`

const INCREMENTAR = `SubProceso Incrementar(n Por Referencia)
    Definir n Como Entero;
    n <- n + 1;
FinSubProceso
Algoritmo Incremento
    Definir edad Como Entero;
    edad <- 17;
    Incrementar(edad);
    Escribir edad;
FinAlgoritmo
`

describe("importar pseudocódigo al diagrama", () => {
  it("reconstruye el área, el mayor, la tabla y el promedio", () => {
    for (const source of [AREA, MAYOR, TABLA, PROMEDIO, ARREGLO]) {
      expect(toSource(importSource(source).program)).toBe(source)
    }
  })

  it("vuelve a escribir el ejemplo armado en el diagrama", () => {
    const source = toSource(guessingGame())
    expect(toSource(importSource(source).program)).toBe(source)
  })

  it("conserva Dimension y una llamada como figuras de texto", () => {
    const program = importSource(ARREGLO).program
    const dimension = program.body.find((step) => step.kind === "libre")
    expect(dimension).toMatchObject({ kind: "libre", text: "Dimension numeros[5] Como Entero", call: false })
    const call = importSource(INCREMENTAR).program.body.find((step) => step.kind === "libre")
    expect(call).toMatchObject({ kind: "libre", text: "Incrementar(edad)", call: true })
  })

  it("conserva las funciones y los procedimientos junto al algoritmo", () => {
    expect(toSource(importSource(DOBLAR).program)).toBe(DOBLAR)
    expect(toSource(importSource(INCREMENTAR).program)).toBe(INCREMENTAR)
    expect(importSource(DOBLAR).notes.some((note) => note.includes("funciones"))).toBe(false)
  })

  it("arma un Según, un Repetir y un Para con paso", () => {
    const source = toSource(
      importSource(`Algoritmo Menu
    Segun opcion Hacer
        1:
            Escribir "uno";
        2, 3:
            Escribir "varios";
        De Otro Modo:
            Escribir "otro";
    FinSegun
    Repetir
        Leer dato;
    Hasta Que dato = 0;
    Para i <- 0 Hasta 4 Con Paso 2 Hacer
        Escribir i;
    FinPara
FinAlgoritmo
`).program,
    )
    expect(source).toContain("Segun opcion Hacer")
    expect(source).toContain("2, 3:")
    expect(source).toContain('Escribir "otro";')
    expect(source).toContain("Hasta Que dato = 0")
    expect(source).toContain("Para i <- 0 Hasta 4 Con Paso 2 Hacer")
  })

  it("separa cada opción del Según aunque no lleve punto y coma", () => {
    const result = importSource(`Algoritmo dias_segun
    Definir dia Como Entero
    Escribir "Indica el numero de dia: "
    Leer dia
    Segun dia Hacer
        1:
            Escribir "Lunes"
        2:
            Escribir "Martes"
        3:
            Escribir "Miercoles"
        4:
            Escribir "Jueves"
        5:
            Escribir "Viernes"
        6:
            Escribir "Sabado"
        7:
            Escribir "Domingo"
        De Otro Modo:
            Escribir "Dia no valido"
    FinSegun
FinAlgoritmo
`)
    const segun = result.program.body.find((step) => step.kind === "segun")
    expect(segun).toMatchObject({
      kind: "segun",
      expression: "dia",
      cases: [
        { label: "1", body: [{ kind: "escribir", text: '"Lunes"' }] },
        { label: "2", body: [{ kind: "escribir", text: '"Martes"' }] },
        { label: "3", body: [{ kind: "escribir", text: '"Miercoles"' }] },
        { label: "4", body: [{ kind: "escribir", text: '"Jueves"' }] },
        { label: "5", body: [{ kind: "escribir", text: '"Viernes"' }] },
        { label: "6", body: [{ kind: "escribir", text: '"Sabado"' }] },
        { label: "7", body: [{ kind: "escribir", text: '"Domingo"' }] },
      ],
      other: [{ kind: "escribir", text: '"Dia no valido"' }],
    })
    const scene = layoutProgram(result.program)
    const header = scene.nodes.find((node) => node.figure === "switch")
    expect(header?.cases?.map((item) => item.label)).toEqual(["1", "2", "3", "4", "5", "6", "7", null])
  })

  it("deja la variable del Escribir en la instrucción y no en el caso", () => {
    const result = importSource(`Algoritmo calculadora
    Definir opcion_ Como Caracter
    Definir num1, num2, total Como Real
    Leer opcion_
    Segun opcion_ Hacer
        '+':
            Escribir "Seleccionaste la SUMA"
            Escribir "Ingresa el numero 1: "
            Leer num1
            Escribir "Ingresa el numero 2: "
            Leer num2
            total <- num1 + num2
            Escribir "La suma es: ", total
        '-':
            Escribir "Seleccionaste la RESTA"
            Leer num1
            Leer num2
            total <- num1 - num2
            Escribir "La resta es: ", total
        '*':
            Escribir "La multiplicacion es: ", total
        De Otro Modo:
            Escribir "Operacion no valida"
    FinSegun
FinAlgoritmo
`)
    const segun = result.program.body.find((step) => step.kind === "segun")
    expect(segun).toMatchObject({
      kind: "segun",
      expression: "opcion_",
      cases: [
        {
          label: "'+'",
          body: [
            { kind: "escribir", text: '"Seleccionaste la SUMA"' },
            { kind: "escribir", text: '"Ingresa el numero 1: "' },
            { kind: "leer", text: "num1" },
            { kind: "escribir", text: '"Ingresa el numero 2: "' },
            { kind: "leer", text: "num2" },
            { kind: "asignar", destination: "total", expression: "num1 + num2" },
            { kind: "escribir", text: '"La suma es: ", total' },
          ],
        },
        {
          label: "'-'",
          body: [
            { kind: "escribir", text: '"Seleccionaste la RESTA"' },
            { kind: "leer", text: "num1" },
            { kind: "leer", text: "num2" },
            { kind: "asignar", destination: "total", expression: "num1 - num2" },
            { kind: "escribir", text: '"La resta es: ", total' },
          ],
        },
        { label: "'*'", body: [{ kind: "escribir", text: '"La multiplicacion es: ", total' }] },
      ],
      other: [{ kind: "escribir", text: '"Operacion no valida"' }],
    })
    expect(toSource(result.program)).not.toContain(", total '-':")
  })

  it("recupera un comentario de línea y lo escribe sin punto y coma", () => {
    const source = ["// titulo", "Algoritmo Notas", "    // preparar", '    Escribir "hola";', "FinAlgoritmo", ""].join("\n")
    const program = importSource(source).program
    expect(program.body[0]).toMatchObject({ kind: "comentario", text: "preparar" })
    expect(program.body[1]).toMatchObject({ kind: "escribir", text: '"hola"' })
    const again = toSource(program)
    expect(again).toContain("    // preparar\n")
    expect(again).not.toContain("// preparar;")
  })

  it("avisa si el texto no trae un algoritmo", () => {
    expect(() => importSource('Escribir "Hola";\n')).toThrow(/fuera del algoritmo/)
  })
})
