import { afterEach, describe, expect, it } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import ts from 'typescript'
import { i18n, normalizeLocale, setLocale, t } from './index'
import en from './en.json'

afterEach(async () => { await setLocale('zh-CN') })
describe('complete bilingual resources', () => {
  it('switches language, interpolates values, and falls back predictably', async () => {
    await setLocale('en')
    expect(t('登录')).toBe('Sign in')
    expect(t('第 {{v0}} 步，共 {{v1}} 步', {v0: 2, v1: 4})).toBe('Step 2 of 4')
    await setLocale('zh-CN')
    expect(t('登录')).toBe('登录')
    expect(normalizeLocale('en-GB')).toBe('en')
    expect(normalizeLocale('zh-Hans-CN')).toBe('zh-CN')
    expect(i18n.language).toBe('zh-CN')
  })
  it('provides an English entry for every static translation key in the UI', () => {
    const missing: string[] = []
    function inspect(dir: string) {
      for (const entry of readdirSync(dir, {withFileTypes: true})) {
        const file = join(dir, entry.name)
        if (entry.isDirectory()) { inspect(file); continue }
        if (!/\.tsx?$/.test(file) || file.endsWith('.test.ts')) continue
        const source = ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, file.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
        function visit(node: ts.Node) {
          if (ts.isCallExpression(node) && node.expression.getText(source) === 't' && node.arguments[0] && ts.isStringLiteral(node.arguments[0])) {
            const key = node.arguments[0].text
            if (!(key in en)) missing.push(key)
          }
          ts.forEachChild(node, visit)
        }
        visit(source)
      }
    }
    inspect(join(process.cwd(), 'src'))
    expect(missing).toEqual([])
    expect(Object.values(en).some(value => /[\u4e00-\u9fff]/.test(value))).toBe(false)
  })
})
