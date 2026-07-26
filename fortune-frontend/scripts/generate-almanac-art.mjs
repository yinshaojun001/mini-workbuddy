import { mkdir } from 'node:fs/promises'
import { chromium } from '@playwright/test'

await mkdir(new URL('../public/assets/', import.meta.url), { recursive: true })
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1200, height: 1600 }, deviceScaleFactor: 1 })
await page.setContent('<canvas id="art" width="1200" height="1600"></canvas>')
await page.evaluate(() => {
  const canvas = document.querySelector('#art')
  const context = canvas.getContext('2d')
  let seed = 20260724
  const random = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296)
  context.fillStyle = '#173a31'
  context.fillRect(0, 0, 1200, 1600)
  context.strokeStyle = 'rgba(196, 169, 112, .18)'
  context.lineWidth = 1
  for (let x = 80; x < 1200; x += 80) { context.beginPath(); context.moveTo(x, 0); context.lineTo(x, 1600); context.stroke() }
  for (let y = 80; y < 1600; y += 80) { context.beginPath(); context.moveTo(0, y); context.lineTo(1200, y); context.stroke() }
  context.strokeStyle = 'rgba(215, 226, 216, .24)'
  for (const radius of [190, 330, 470]) { context.beginPath(); context.arc(600, 700, radius, 0, Math.PI * 2); context.stroke() }
  const stars = Array.from({ length: 86 }, () => ({ x: 110 + random() * 980, y: 120 + random() * 1120, r: 1.5 + random() * 4 }))
  context.strokeStyle = 'rgba(208, 185, 135, .34)'
  for (let i = 1; i < stars.length; i += 3) { context.beginPath(); context.moveTo(stars[i - 1].x, stars[i - 1].y); context.lineTo(stars[i].x, stars[i].y); context.stroke() }
  for (const star of stars) { context.beginPath(); context.fillStyle = random() > .82 ? '#b95a45' : '#d3c49d'; context.arc(star.x, star.y, star.r, 0, Math.PI * 2); context.fill() }
  context.strokeStyle = 'rgba(166, 61, 47, .7)'; context.lineWidth = 5; context.strokeRect(850, 1280, 170, 170)
  context.fillStyle = 'rgba(240, 244, 238, .035)'
  for (let i = 0; i < 6500; i += 1) context.fillRect(random() * 1200, random() * 1600, 1 + random() * 2, 1)
})
await page.locator('#art').screenshot({ path: new URL('../public/assets/almanac-map.png', import.meta.url).pathname })
await browser.close()
