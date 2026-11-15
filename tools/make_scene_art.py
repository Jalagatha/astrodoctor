"""Generate templates/wellbeing/_art.html: one decorative SVG illustration per scene.

Usage: python tools/make_scene_art.py templates/wellbeing/_art.html
Elements with wb-anim-* classes animate only inside an .is-animated container.
"""
import random
import sys

W, H = 400, 250
rng = random.Random(42)


def svg(key, body, defs):
    return (f'<svg class="wb-art wb-art-{key}" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" '
            f'aria-hidden="true" focusable="false"><defs>{defs}</defs>{body}</svg>')


def grad(gid, stops, x2="0", y2="1"):
    s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    return f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{s}</linearGradient>'


def radial(gid, stops):
    s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
    return f'<radialGradient id="{gid}">{s}</radialGradient>'


def stars(n, max_y, cls="wb-anim-twinkle", color="#fff"):
    out = []
    for i in range(n):
        x, y, r = rng.uniform(0, W), rng.uniform(0, max_y), rng.choice((0.6, 0.8, 1, 1.3))
        out.append(f'<circle class="{cls}" style="animation-delay:{rng.uniform(0, 4):.1f}s" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{color}" opacity="{rng.uniform(.4, .95):.2f}"/>')
    return "".join(out)


def pines(count, base, h_range, w_range, fill, opacity=1.0, jitter=0):
    path = []
    step = W / count
    for i in range(count + 1):
        cx = i * step + rng.uniform(-jitter, jitter)
        h, w = rng.uniform(*h_range), rng.uniform(*w_range)
        # three stacked triangles for a fir silhouette
        for k, scale in enumerate((1.0, 0.78, 0.56)):
            top = base - h * (0.45 + 0.27 * k)
            bottom = base - h * 0.3 * k
            half = w * scale / 2
            path.append(f"M{cx - half:.0f} {bottom:.0f}L{cx:.0f} {top:.0f}L{cx + half:.0f} {bottom:.0f}Z")
    return f'<path d="{"".join(path)}" fill="{fill}" opacity="{opacity}"/>'


def family():
    defs = grad("wb-fam-sky", [("0", "#8fc7ff"), (".55", "#ffd9ae"), ("1", "#ffb3a0")]) + \
        radial("wb-fam-sun", [("0", "#fff6d5", 1), (".45", "#ffe7a3", .7), ("1", "#ffd27a", 0)])
    house = lambda x, y, w, h, wall, roof: (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{wall}"/>'
        f'<path d="M{x - 6} {y + 2}L{x + w / 2} {y - h * .55}L{x + w + 6} {y + 2}Z" fill="{roof}"/>'
        f'<rect x="{x + w * .18}" y="{y + h * .25}" width="{w * .22}" height="{h * .25}" rx="2" fill="#ffd772"/>'
        f'<rect x="{x + w * .6}" y="{y + h * .25}" width="{w * .22}" height="{h * .25}" rx="2" fill="#ffd772"/>'
        f'<rect x="{x + w * .4}" y="{y + h * .58}" width="{w * .2}" height="{h * .42}" rx="2" fill="#9c5b4a"/>')
    body = (
        f'<rect width="{W}" height="{H}" fill="url(#wb-fam-sky)"/>'
        '<circle cx="312" cy="78" r="70" fill="url(#wb-fam-sun)"/><circle cx="312" cy="78" r="26" fill="#fff4cf"/>'
        '<g class="wb-anim-drift" fill="#fff" opacity=".75"><ellipse cx="90" cy="60" rx="34" ry="11"/><ellipse cx="112" cy="52" rx="22" ry="12"/>'
        '<ellipse cx="220" cy="38" rx="26" ry="8"/><ellipse cx="236" cy="32" rx="16" ry="9"/></g>'
        '<path d="M0 160Q70 120 150 150T300 140T400 150V250H0Z" fill="#f0a99c" opacity=".55"/>'
        + house(34, 132, 62, 48, "#fde7d6", "#e0705a") + house(116, 144, 48, 38, "#f9d9c6", "#c8475c")
        + '<rect x="196" y="150" width="6" height="30" fill="#7b5a44"/><circle cx="199" cy="140" r="20" fill="#74b06b"/><circle cx="186" cy="150" r="13" fill="#6aa361"/>'
        '<path d="M0 182Q120 170 230 186T400 180V250H0Z" fill="#a9d68a"/>'
        '<path d="M150 250Q210 205 400 196V214Q260 222 214 250Z" fill="#f2d7b6"/>'
        # adult and child holding hands
        '<g fill="#3f3b6e"><circle cx="262" cy="176" r="8"/><rect x="254" y="185" width="16" height="30" rx="7"/>'
        '<rect x="255" y="212" width="5" height="16" rx="2"/><rect x="264" y="212" width="5" height="16" rx="2"/>'
        '<circle cx="292" cy="190" r="6.5"/><rect x="285" y="197" width="13" height="21" rx="6"/>'
        '<rect x="286" y="215" width="4" height="12" rx="2"/><rect x="293" y="215" width="4" height="12" rx="2"/></g>'
        '<rect x="296" y="198" width="8" height="12" rx="2" fill="#f3a25b"/>'
        '<path d="M269 197Q278 204 286 201" stroke="#3f3b6e" stroke-width="3" fill="none" stroke-linecap="round"/>'
    )
    return svg("family", body, defs)


def nature():
    defs = grad("wb-nat-sky", [("0", "#3d7a68"), (".6", "#1d4a3f"), ("1", "#0f2c26")])
    drops = []
    for _ in range(70):
        x, y = rng.uniform(-20, W), rng.uniform(-60, H)
        drops.append(f"M{x:.0f} {y:.0f}l-4 12")
    rain = '<path d="' + "".join(drops) + '" stroke="#cdeee4" stroke-width="1.2" stroke-linecap="round" opacity=".45"/>'
    body = (
        f'<rect width="{W}" height="{H}" fill="url(#wb-nat-sky)"/>'
        '<ellipse cx="200" cy="120" rx="260" ry="40" fill="#e6fff6" opacity=".07"/>'
        + pines(9, 168, (60, 90), (34, 46), "#3c806b", .55, 10)
        + '<rect y="150" width="400" height="30" fill="#e6fff6" opacity=".06"/>'
        + pines(7, 205, (80, 120), (44, 60), "#245748", .85, 14)
        + pines(5, 250, (120, 160), (64, 84), "#123a30", 1, 18)
        + f'<g class="wb-anim-rain">{rain}<g transform="translate(0 -250)">{rain}</g></g>'
        '<ellipse class="wb-anim-ripple" cx="120" cy="236" rx="16" ry="3" fill="none" stroke="#cdeee4" opacity=".4"/>'
        '<ellipse class="wb-anim-ripple" style="animation-delay:1.3s" cx="300" cy="242" rx="12" ry="2.5" fill="none" stroke="#cdeee4" opacity=".4"/>'
    )
    return svg("nature", body, defs)


def learning():
    defs = grad("wb-lrn-sky", [("0", "#4257c9"), (".55", "#283383"), ("1", "#161b4a")]) + \
        radial("wb-lrn-globe", [("0", "#8ea6ff", 1), (".7", "#3a4dc0", 1), ("1", "#26318a", 1)]) + \
        radial("wb-lrn-glow", [("0", "#a5b4fc", .55), ("1", "#a5b4fc", 0)])
    glyphs = [("A", 92, 82, 30), ("あ", 302, 70, 26), ("Ж", 70, 170, 24), ("ع", 330, 168, 28), ("文", 140, 46, 22),
              ("Ω", 262, 40, 20), ("ñ", 352, 116, 22), ("λ", 44, 120, 20)]
    text = "".join(
        f'<text class="wb-anim-float" style="animation-delay:{i * .6:.1f}s" x="{x}" y="{y}" font-size="{s}" '
        f'font-family="system-ui, sans-serif" font-weight="700" fill="#e0e7ff" opacity=".85" text-anchor="middle">{g}</text>'
        for i, (g, x, y, s) in enumerate(glyphs))
    body = (
        f'<rect width="{W}" height="{H}" fill="url(#wb-lrn-sky)"/>' + stars(40, 250)
        + '<circle cx="200" cy="128" r="104" fill="url(#wb-lrn-glow)"/>'
        '<circle cx="200" cy="128" r="62" fill="url(#wb-lrn-globe)"/>'
        '<g fill="none" stroke="#c7d2fe" stroke-opacity=".45" stroke-width="1.2">'
        '<ellipse cx="200" cy="128" rx="62" ry="22"/><ellipse cx="200" cy="128" rx="62" ry="44"/>'
        '<ellipse cx="200" cy="128" rx="22" ry="62"/><ellipse cx="200" cy="128" rx="44" ry="62"/>'
        '<path d="M138 128H262M200 66V190"/></g>'
        '<ellipse cx="200" cy="128" rx="92" ry="20" fill="none" stroke="#f0abfc" stroke-opacity=".5" stroke-width="1.5" transform="rotate(-18 200 128)"/>'
        + text +
        '<ellipse cx="200" cy="232" rx="150" ry="16" fill="#0e1236" opacity=".7"/>'
    )
    return svg("learning", body, defs)


def active():
    defs = grad("wb-act-sky", [("0", "#5fb8ff"), (".6", "#b9e3ff"), ("1", "#ffe7b0")]) + \
        radial("wb-act-sun", [("0", "#fff7c2", 1), (".4", "#ffe066", .8), ("1", "#ffd23f", 0)])
    body = (
        f'<rect width="{W}" height="{H}" fill="url(#wb-act-sky)"/>'
        '<circle cx="70" cy="62" r="62" fill="url(#wb-act-sun)"/><circle cx="70" cy="62" r="22" fill="#fff6c9"/>'
        '<g class="wb-anim-drift" fill="#fff" opacity=".85"><ellipse cx="270" cy="50" rx="30" ry="10"/><ellipse cx="292" cy="42" rx="20" ry="11"/></g>'
        '<rect y="128" width="400" height="34" fill="#2f9fd6"/><path d="M0 132H400" stroke="#d6f1ff" stroke-width="2" stroke-dasharray="14 10" opacity=".6"/>'
        '<path d="M0 158Q90 128 200 150T400 140V250H0Z" fill="#86cf6c"/>'
        '<path d="M0 196Q140 170 260 190T400 184V250H0Z" fill="#5fb055"/>'
        '<path d="M0 226Q150 196 400 214V230Q170 214 0 250Z" fill="#f0dcae"/>'
        # goal
        '<path d="M318 206V170H384V206" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/>'
        '<path d="M322 174L380 202M322 202L380 174" stroke="#fff" stroke-width=".8" opacity=".6"/>'
        # bike
        '<g fill="none" stroke="#24304a" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="92" cy="214" r="15"/><circle cx="142" cy="214" r="15"/>'
        '<path d="M92 214L110 186H134L142 214M110 186L118 214H92M128 178H140M108 178L112 186"/></g>'
        '<path d="M106 178H116" stroke="#e85d3f" stroke-width="5" stroke-linecap="round"/>'
        # ball
        '<g class="wb-anim-bounce"><ellipse cx="262" cy="222" rx="10" ry="2.5" fill="#24304a" opacity=".25" class="wb-ball-shadow"/>'
        '<g class="wb-ball"><circle cx="262" cy="196" r="12" fill="#fff" stroke="#24304a" stroke-width="2"/>'
        '<path d="M262 190l5.5 4-2 6.5h-7l-2-6.5z" fill="#24304a"/></g></g>'
    )
    return svg("active", body, defs)


def calm():
    defs = grad("wb-calm-sky", [("0", "#161a46"), (".55", "#463c8c"), ("1", "#c681aa")]) + \
        radial("wb-calm-glow", [("0", "#ffe9a8", .9), ("1", "#ffe9a8", 0)]) + \
        '<mask id="wb-calm-moon"><rect width="400" height="250" fill="#fff"/><circle cx="318" cy="52" r="20" fill="#000"/></mask>' + \
        radial("wb-calm-earth", [("0", "#7dd3fc", 1), (".7", "#2563eb", 1), ("1", "#1e3a8a", 1)])
    flowers = []
    for _ in range(16):
        x, y = rng.uniform(20, 380), rng.uniform(208, 240)
        c = rng.choice(("#f0abfc", "#fde68a", "#c4b5fd", "#fbcfe8"))
        flowers.append(f'<path d="M{x:.0f} {y + 14:.0f}V{y:.0f}" stroke="#2c2659" stroke-width="2"/><circle cx="{x:.0f}" cy="{y:.0f}" r="3.2" fill="{c}"/>')
    flies = "".join(
        f'<circle class="wb-anim-firefly" style="animation-delay:{rng.uniform(0, 5):.1f}s" cx="{rng.uniform(30, 370):.0f}" '
        f'cy="{rng.uniform(150, 215):.0f}" r="1.8" fill="#fde68a"/>' for _ in range(12))
    body = (
        f'<rect width="{W}" height="{H}" fill="url(#wb-calm-sky)"/>' + stars(55, 150)
        + '<circle cx="308" cy="58" r="22" fill="#fdf3c6" mask="url(#wb-calm-moon)"/>'
        '<circle cx="76" cy="70" r="13" fill="url(#wb-calm-earth)"/><path d="M70 64q5 2 4 7t5 6" stroke="#86efac" stroke-width="2" fill="none" opacity=".8"/>'
        '<path d="M0 182Q100 150 210 172T400 160V250H0Z" fill="#2f2862"/>'
        '<g fill="#3b3277"><circle cx="40" cy="196" r="26"/><circle cx="82" cy="204" r="20"/><circle cx="346" cy="192" r="28"/><circle cx="380" cy="204" r="18"/></g>'
        '<path d="M0 214Q200 196 400 214V250H0Z" fill="#231d4c"/>'
        + "".join(flowers)
        + '<circle cx="204" cy="190" r="34" fill="url(#wb-calm-glow)" class="wb-anim-glow"/>'
        '<rect x="198" y="182" width="12" height="16" rx="3" fill="#ffe6a0"/><path d="M204 182V172M196 182H212" stroke="#1b1740" stroke-width="2"/>'
        '<path d="M204 198V226" stroke="#1b1740" stroke-width="2.5"/>'
        + flies
    )
    return svg("calm", body, defs)


scenes = {"family": family(), "nature": nature(), "learning": learning(), "active": active(), "calm": calm()}
parts = ["{# Generated decorative scene art. Include with: {% include \"wellbeing/_art.html\" with key=scene.key %} #}"]
for i, (key, markup) in enumerate(scenes.items()):
    parts.append(("{% if" if i == 0 else "{% elif") + f' key == "{key}" %}}{markup}')
parts.append("{% endif %}")
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    handle.write("\n".join(parts) + "\n")
print("wrote", sys.argv[1])
