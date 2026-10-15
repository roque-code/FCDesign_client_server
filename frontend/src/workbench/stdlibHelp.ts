const SPANISH: Record<string, { signature: string; summary: string }> = {
  Abs: {
    signature: "Abs(número)",
    summary: "Valor absoluto. Devuelve entero o real, según el argumento.",
  },
  "Raíz": {
    signature: "Raíz(número)",
    summary: "Raíz cuadrada. Devuelve un real.",
  },
  Potencia: {
    signature: "Potencia(base, exponente)",
    summary: "Eleva la base al exponente. Dos enteros dan entero; si hay un real, el resultado es real.",
  },
  Redon: {
    signature: "Redon(número)",
    summary: "Redondea al entero más cercano.",
  },
  Trunc: {
    signature: "Trunc(número)",
    summary: "Quita la parte decimal, sin redondear.",
  },
  Sen: {
    signature: "Sen(radianes)",
    summary: "Seno. El ángulo va en radianes y el resultado es real.",
  },
  Cos: {
    signature: "Cos(radianes)",
    summary: "Coseno. El ángulo va en radianes y el resultado es real.",
  },
  Tan: {
    signature: "Tan(radianes)",
    summary: "Tangente. El ángulo va en radianes y el resultado es real.",
  },
  Ln: {
    signature: "Ln(número)",
    summary: "Logaritmo natural. Devuelve un real.",
  },
  Exp: {
    signature: "Exp(número)",
    summary: "e elevado al número. Devuelve un real.",
  },
  Aleatorio: {
    signature: "Aleatorio() o Aleatorio(inicio, fin)",
    summary: "Sin argumentos, un real entre 0 y 1. Con dos enteros, un entero de ese intervalo, incluidos los extremos.",
  },
  Longitud: {
    signature: "Longitud(cadena)",
    summary: "Cantidad de símbolos de la cadena. Devuelve un entero.",
  },
  Subcadena: {
    signature: "Subcadena(cadena, desde, hasta)",
    summary: "Recorte que incluye ambos extremos. Los índices siguen la configuración del algoritmo.",
  },
  Concatenar: {
    signature: "Concatenar(a, b, …)",
    summary: "Une de 2 a 8 valores en una cadena.",
  },
  "Mayúsculas": {
    signature: "Mayúsculas(cadena)",
    summary: "Pasa el texto a mayúsculas.",
  },
  "Minúsculas": {
    signature: "Minúsculas(cadena)",
    summary: "Pasa el texto a minúsculas.",
  },
  ConvertirANumero: {
    signature: "ConvertirANumero(cadena)",
    summary: "Interpreta el texto como entero o, si lleva punto, como real.",
  },
  ConvertirATexto: {
    signature: "ConvertirATexto(valor)",
    summary: "Escribe el valor como cadena.",
  },
}

const ENGLISH: Record<string, { signature: string; summary: string }> = {
  Abs: { signature: "Abs(number)", summary: "Absolute value. Returns an integer or a real, matching the argument." },
  "Raíz": { signature: "Raíz(number)", summary: "Square root. Returns a real." },
  Potencia: { signature: "Potencia(base, exponent)", summary: "Raises the base to the exponent. Two integers stay integer; a real makes the result real." },
  Redon: { signature: "Redon(number)", summary: "Rounds to the nearest integer." },
  Trunc: { signature: "Trunc(number)", summary: "Drops the fractional part without rounding." },
  Sen: { signature: "Sen(radians)", summary: "Sine. The angle is in radians and the result is real." },
  Cos: { signature: "Cos(radians)", summary: "Cosine. The angle is in radians and the result is real." },
  Tan: { signature: "Tan(radians)", summary: "Tangent. The angle is in radians and the result is real." },
  Ln: { signature: "Ln(number)", summary: "Natural logarithm. Returns a real." },
  Exp: { signature: "Exp(number)", summary: "e raised to the number. Returns a real." },
  Aleatorio: { signature: "Aleatorio() or Aleatorio(start, end)", summary: "With no arguments, a real between 0 and 1. With two integers, an integer in that range, ends included." },
  Longitud: { signature: "Longitud(text)", summary: "Number of symbols in the text. Returns an integer." },
  Subcadena: { signature: "Subcadena(text, from, to)", summary: "A slice that includes both ends. Indexes follow the algorithm setting." },
  Concatenar: { signature: "Concatenar(a, b, …)", summary: "Joins 2 to 8 values into text." },
  "Mayúsculas": { signature: "Mayúsculas(text)", summary: "Turns the text into uppercase." },
  "Minúsculas": { signature: "Minúsculas(text)", summary: "Turns the text into lowercase." },
  ConvertirANumero: { signature: "ConvertirANumero(text)", summary: "Reads the text as an integer, or as a real if it contains a dot." },
  ConvertirATexto: { signature: "ConvertirATexto(value)", summary: "Writes the value as text." },
}

export function stdlibHelp(locale: "es" | "en", name: string) {
  const table = locale === "en" ? ENGLISH : SPANISH
  return table[name] ?? SPANISH[name]
}
