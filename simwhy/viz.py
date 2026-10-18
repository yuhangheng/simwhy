"""Dependency-free SVG height/pressure visualization."""
from html import escape

def render_svg(rows, summary, width=900, height=450):
    left, right, top, bottom = 85, width-25, 35, height-70
    times = [r["time_s"] for r in rows]
    alt = [r["altitude_m"] for r in rows]
    pressure = [r["tank_pressure_pa"] / 1e6 for r in rows]
    ymax = max(0.05, max(alt) * 1.1)
    pmax = max(1.0, pressure[0] * 1.1)
    xmax = max(times)
    def x(t): return left + (right-left)*t/xmax
    def ya(y): return bottom - (bottom-top)*y/ymax
    def yp(p): return bottom - (bottom-top)*p/pmax
    sample = rows[::max(1, len(rows)//350)]
    if sample[-1] is not rows[-1]:
        sample = sample + [rows[-1]]
    pts_a = " ".join(f'{x(r["time_s"]):.1f},{ya(r["altitude_m"]):.1f}' for r in sample)
    pts_p = " ".join(f'{x(r["time_s"]):.1f},{yp(r["tank_pressure_pa"]/1e6):.1f}' for r in sample)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
             '<rect width="100%" height="100%" fill="#111827"/>',
             '<text x="80" y="23" fill="#f9fafb" font-size="17" font-family="sans-serif">Pressurized gas pulse — hypothesis only</text>']
    for j in range(6):
        px=left + (right-left)*j/5
        py=bottom - (bottom-top)*j/5
        lines += [f'<line x1="{px:.1f}" y1="{top}" x2="{px:.1f}" y2="{bottom}" stroke="#374151"/>',
                  f'<line x1="{left}" y1="{py:.1f}" x2="{right}" y2="{py:.1f}" stroke="#374151"/>',
                  f'<text x="{px-9:.1f}" y="{bottom+23}" fill="#aebbc8" font-size="12">{xmax*j/5:.1f}</text>',
                  f'<text x="18" y="{py+4:.1f}" fill="#67e8f9" font-size="12">{ymax*j/5:.2f} m</text>',
                  f'<text x="{right-8}" y="{py+4:.1f}" text-anchor="end" fill="#fbbf24" font-size="12">{pmax*j/5:.1f} MPa</text>']
    lines += [f'<polyline points="{pts_a}" fill="none" stroke="#22d3ee" stroke-width="2.5"/>',
              f'<polyline points="{pts_p}" fill="none" stroke="#f59e0b" stroke-width="2"/>',
              f'<text x="{(left+right)/2:.0f}" y="{height-20}" fill="#d1d5db" text-anchor="middle" font-family="sans-serif">Time (s)</text>',
              f'<text x="{left+5}" y="{top+25}" fill="#67e8f9" font-family="sans-serif">Altitude</text>',
              f'<text x="{left+5}" y="{top+47}" fill="#fbbf24" font-family="sans-serif">Tank pressure (right axis)</text>',
              '<text x="80" y="430" fill="#9ca3af" font-size="11" font-family="sans-serif">Ideal-gas / 1D point mass. Not a verified real vehicle.</text>',
              '</svg>']
    return "\n".join(lines)
