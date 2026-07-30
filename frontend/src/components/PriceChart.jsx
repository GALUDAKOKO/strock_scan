import { useMemo, useState } from 'react'

const WIDTH = 800
const PRICE_HEIGHT = 260
const VOLUME_HEIGHT = 70
const GAP = 12
const PADDING = 28
const UP_COLOR = '#2e7d32'
const DOWN_COLOR = '#d3453f'

/**
 * Dependency-free SVG price + volume chart. Takes an array of candles
 * (oldest first) shaped like { timestamp, close, high, low, open, volume }.
 */
export default function PriceChart({ candles, height = PRICE_HEIGHT + VOLUME_HEIGHT + GAP, emptyMessage }) {
  const [hoverIndex, setHoverIndex] = useState(null)

  const data = useMemo(() => {
    if (!candles || candles.length === 0) return null

    const closes = candles.map((c) => Number(c.close))
    const highs = candles.map((c) => Number(c.high ?? c.close))
    const lows = candles.map((c) => Number(c.low ?? c.close))
    const volumes = candles.map((c) => Number(c.volume ?? 0))

    const minPrice = Math.min(...lows)
    const maxPrice = Math.max(...highs)
    const priceRange = maxPrice - minPrice || 1
    const maxVolume = Math.max(...volumes, 1)

    const plotWidth = WIDTH - PADDING * 2
    const step = candles.length > 1 ? plotWidth / (candles.length - 1) : 0

    const xAt = (index) => PADDING + index * step
    const yAt = (price) => PADDING + (1 - (price - minPrice) / priceRange) * (PRICE_HEIGHT - PADDING * 2)
    const volumeYAt = (volume) =>
      PRICE_HEIGHT + GAP + (VOLUME_HEIGHT - (volume / maxVolume) * VOLUME_HEIGHT)

    const linePoints = closes.map((close, index) => `${xAt(index)},${yAt(close)}`).join(' ')
    const areaPoints = `${xAt(0)},${PRICE_HEIGHT - PADDING} ${linePoints} ${xAt(closes.length - 1)},${
      PRICE_HEIGHT - PADDING
    }`

    return { closes, volumes, minPrice, maxPrice, xAt, yAt, volumeYAt, linePoints, areaPoints, step }
  }, [candles])

  if (!data) {
    return <p className="empty-message">{emptyMessage || 'No history to chart.'}</p>
  }

  const { closes, volumes, minPrice, maxPrice, xAt, yAt, volumeYAt, linePoints, areaPoints, step } = data
  const barWidth = Math.max(step * 0.6, 1)
  const hovered = hoverIndex !== null ? candles[hoverIndex] : null

  return (
    <div className="price-chart">
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        className="price-chart-svg"
        onMouseLeave={() => setHoverIndex(null)}
      >
        {/* Price gridlines + labels */}
        <line x1={PADDING} y1={PADDING} x2={WIDTH - PADDING} y2={PADDING} stroke="var(--border)" strokeWidth="1" />
        <line
          x1={PADDING}
          y1={PRICE_HEIGHT - PADDING}
          x2={WIDTH - PADDING}
          y2={PRICE_HEIGHT - PADDING}
          stroke="var(--border)"
          strokeWidth="1"
        />
        <text x={PADDING} y={PADDING - 6} fontSize="11" fill="var(--text)">
          {maxPrice.toFixed(2)}
        </text>
        <text x={PADDING} y={PRICE_HEIGHT - PADDING + 16} fontSize="11" fill="var(--text)">
          {minPrice.toFixed(2)}
        </text>

        {/* Price area + line */}
        <polygon points={areaPoints} fill="var(--accent-bg, rgba(170,59,255,0.12))" stroke="none" />
        <polyline points={linePoints} fill="none" stroke="var(--accent)" strokeWidth="2" />

        {/* Volume bars */}
        {volumes.map((volume, index) => (
          <rect
            key={index}
            x={xAt(index) - barWidth / 2}
            y={volumeYAt(volume)}
            width={barWidth}
            height={PRICE_HEIGHT + GAP + VOLUME_HEIGHT - volumeYAt(volume)}
            fill={
              index === 0 || closes[index] >= closes[index - 1]
                ? `${UP_COLOR}55`
                : `${DOWN_COLOR}55`
            }
          />
        ))}

        {/* Hover target overlay */}
        {closes.map((_, index) => (
          <rect
            key={`hover-${index}`}
            x={xAt(index) - step / 2}
            y={0}
            width={Math.max(step, 1)}
            height={height}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(index)}
          />
        ))}

        {hoverIndex !== null && (
          <line
            x1={xAt(hoverIndex)}
            y1={PADDING}
            x2={xAt(hoverIndex)}
            y2={PRICE_HEIGHT - PADDING}
            stroke="var(--text)"
            strokeWidth="1"
            strokeDasharray="3,3"
          />
        )}
        {hoverIndex !== null && (
          <circle cx={xAt(hoverIndex)} cy={yAt(closes[hoverIndex])} r="3.5" fill="var(--accent)" />
        )}
      </svg>

      <div className="price-chart-hover">
        {hovered ? (
          <>
            <span>{new Date(hovered.timestamp).toLocaleDateString()}</span>
            <span>{Number(hovered.close).toFixed(2)}</span>
            <span>{Number(hovered.volume ?? 0).toLocaleString()}</span>
          </>
        ) : (
          <span>&nbsp;</span>
        )}
      </div>
    </div>
  )
}
