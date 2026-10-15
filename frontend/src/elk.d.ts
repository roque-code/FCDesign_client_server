declare module "elkjs/lib/elk.bundled.js" {
  export default class ELK {
    layout(graph: object): Promise<{
      children?: Array<{ id: string; x?: number; y?: number; width?: number; height?: number }>
      edges?: Array<{
        id: string
        sections?: Array<{
          startPoint: { x: number; y: number }
          endPoint: { x: number; y: number }
          bendPoints?: Array<{ x: number; y: number }>
        }>
      }>
    }>
  }
}
