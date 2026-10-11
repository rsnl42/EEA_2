"""Helpers shared by the page builders (templates, output, shared CSS)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
DEFAULT_XLSX = ROOT / "data" / "digital_devices_AI_chapter4.xlsx"
DOCS = ROOT / "docs"


TOOLTIP_SCRIPT = """<script>
(function(){
  let tt = document.getElementById('ui-tooltip');
  if(!tt){
    tt = document.createElement('div');
    tt.id = 'ui-tooltip';
    tt.className = 'ui-tooltip';
    tt.setAttribute('aria-hidden', 'true');
    document.body.appendChild(tt);
  }
  let activeEl = null;

  function findTarget(el){
    while(el && el !== document.body && el !== document.documentElement){
      if(el.hasAttribute && el.hasAttribute('title')){
        const titleText = el.getAttribute('title');
        if(titleText){
          el.setAttribute('data-tooltip', titleText);
          el.removeAttribute('title');
        }
      }
      if(el.tagName === 'g' || el.tagName === 'circle' || el.tagName === 'path' || el.tagName === 'rect'){
        const tChild = el.querySelector && el.querySelector('title');
        if(tChild && tChild.textContent){
          el.setAttribute('data-tooltip', tChild.textContent);
          tChild.remove();
        }
      }
      if(el.hasAttribute && el.hasAttribute('data-tooltip')){
        return el;
      }
      el = el.parentElement;
    }
    return null;
  }

  function positionTooltip(e){
    if(!tt.classList.contains('visible')) return;
    const pad = 10;
    const mx = e.clientX;
    const my = e.clientY;

    tt.style.left = mx + 'px';
    tt.style.top = (my - 12) + 'px';
    tt.style.transform = 'translate(-50%, -100%)';

    const rect = tt.getBoundingClientRect();
    if(rect.top < pad){
      tt.style.top = (my + 22) + 'px';
      tt.style.transform = 'translate(-50%, 0)';
    }

    const curRect = tt.getBoundingClientRect();
    if(curRect.left < pad){
      tt.style.left = (pad + curRect.width / 2) + 'px';
    } else if(curRect.right > window.innerWidth - pad){
      tt.style.left = (window.innerWidth - pad - curRect.width / 2) + 'px';
    }
  }

  document.addEventListener('mouseover', function(e){
    const target = findTarget(e.target);
    if(target){
      activeEl = target;
      const text = target.getAttribute('data-tooltip');
      if(text){
        tt.textContent = text;
        tt.classList.add('visible');
        positionTooltip(e);
      }
    }
  }, true);

  document.addEventListener('mousemove', function(e){
    if(activeEl){
      positionTooltip(e);
    }
  }, true);

  document.addEventListener('mouseout', function(e){
    if(activeEl){
      const target = findTarget(e.relatedTarget);
      if(target !== activeEl){
        activeEl = null;
        tt.classList.remove('visible');
      }
    }
  }, true);
})();
</script>"""


def load_template(name: str) -> str:
    """Read templates/<name> and inline the shared stylesheet (%%BASE_CSS%%)."""
    html = (TEMPLATES / name).read_text(encoding="utf-8")
    html = html.replace("%%BASE_CSS%%", (TEMPLATES / "base.css").read_text(encoding="utf-8"))
    if "ui-tooltip" not in html:
        if "</body>" in html:
            html = html.replace("</body>", f"{TOOLTIP_SCRIPT}\n</body>")
        else:
            html += TOOLTIP_SCRIPT
    return html


def fill(html: str, values: dict) -> str:
    """Replace %%KEY%% placeholders; fail loudly if any is missing or left over."""
    for key, val in values.items():
        token = f"%%{key}%%"
        if token not in html:
            raise SystemExit(f"Template is missing placeholder {token}")
        html = html.replace(token, val)
    if "%%" in html:
        left = sorted({w for w in html.split("%%")[1::2] if w.isupper()})
        if left:
            raise SystemExit(f"Unfilled placeholders: {left}")
    return html


def write_page(out: Path, html: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    (DOCS / ".nojekyll").touch()  # stop GitHub Pages running Jekyll
