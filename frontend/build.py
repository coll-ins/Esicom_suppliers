#!/usr/bin/env python3
"""Dependency-free static production builder for Esicom Suppliers."""
from pathlib import Path
import json, os, shutil, re, sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'
ASSETS = ROOT / 'public'
NAVY = '#183c35'
PAGES = {
 '/': {'title':'Everything your office', 'highlight':'needs.', 'eyebrow':'A Nairobi supplier for the workday', 'intro':'Everyday stationery, printing supplies and branded merchandise. Tell us what you need; we’ll take it from there.', 'image':'/images/photography/meeting-room.webp', 'kind':'home'},
 '/office-supplies/': {'title':'The everyday essentials.', 'eyebrow':'OFFICE SUPPLIES', 'intro':'Pens, paper, notebooks and office supplies for the workday.', 'image':'/images/photography/stock-boxed-pens.webp', 'items':['Pens and writing materials','Notebooks, pads and diaries','Files and folders','Printing paper and desk essentials','Office stationery for teams and organisations'], 'kind':'detail'},
 '/computer-consumables/': {'title':'Keep work moving.', 'eyebrow':'COMPUTER CONSUMABLES', 'intro':'Toners, ink cartridges and computer essentials. Share your printer model and we’ll help you find the right fit.', 'image':'/images/photography/computer.webp', 'items':['Printer toners','Ink cartridges','Computer appliances and accessories','Consumable sourcing enquiries','Product model and specification checks before quotation'], 'kind':'detail'},
 '/bulk-printing/': {'title':'Let’s get your print job sorted.', 'eyebrow':'BULK PRINTING', 'intro':'Tell us what you’re printing, how many you need and when you need them.', 'image':'/images/photography/printing.webp', 'items':['Bulk printed business materials','Business documents and stationery','Quantity, size and finish discussions','Print-ready artwork coordination','Quotation based on your brief'], 'kind':'detail'},
 '/branding/': {'title':'Give your brand a useful life.', 'eyebrow':'CORPORATE BRANDING', 'intro':'Branded shirts, business cards, diaries and practical merchandise. Bring your logo and tell us what you have in mind.', 'image':'/images/photography/apparel.webp', 'items':['Branded shirts and apparel','Business cards','Branded diaries and stationery','Asset tags and identification','Custom corporate branding enquiries'], 'kind':'branding'},
 '/about/': {'title':'One local team for the workday.', 'eyebrow':'ABOUT ESICOM SUPPLIERS', 'intro':'We help Nairobi businesses source everyday office supplies, printing and branded merchandise.', 'image':'/images/photography/meeting-room.webp', 'items':['Office stationery and workplace essentials','Printing paper, files, notebooks and pens','Toners, cartridges and computer-related supplies','Bulk printing for business materials','Branded shirts, business cards, diaries and asset tags'], 'kind':'detail'},
 '/contact/': {'title':'What can we help you find?', 'eyebrow':'CONTACT · REQUEST A QUOTE', 'intro':'Send us your list, product photo or print brief. Our team in Nairobi will take it from there.', 'image':'/images/photography/workspace.webp', 'kind':'contact'},
 '/send-file/': {'title':'Send a file to Esicom', 'eyebrow':'FILE UPLOAD', 'intro':'Upload a document or image, convert it if needed, and send it to our team.', 'image':'', 'kind':'upload'},
 '/file-qr/': {'title':'Scan to send a file', 'eyebrow':'FILE UPLOAD QR', 'intro':'Print this QR code so customers can open the secure file upload page on their phones.', 'image':'', 'kind':'qr'},
 '/paper-filing/': {'title':'Paper, pens and the rest.', 'eyebrow':'PAPER & FILING', 'intro':'Reams of copy paper, boxed stationery, files and folders. Let us know what your office needs.', 'image':'/images/photography/stock-copy-paper.webp', 'items':['Copy paper and reams','Files and folders','Notebooks and writing pads','Document organisation supplies','Bulk supply enquiries for offices and teams'], 'kind':'detail'},
 '/business-cards/': {'title':'Business cards, made personal.', 'eyebrow':'BUSINESS CARDS', 'intro':'Tell us about the artwork, quantity and finish you have in mind.', 'image':'/images/photography/printing.webp', 'items':['Business card printing enquiries','Artwork and design file coordination','Quantity and finish discussions','Quotation based on specifications'], 'kind':'detail'},
 '/branded-apparel/': {'title':'Merchandise made yours.', 'eyebrow':'BRANDED APPAREL', 'intro':'Bring your logo and team requirements. We’ll discuss apparel and other branded items with you.', 'image':'/images/photography/apparel.webp', 'items':['Branded shirts','Team and event apparel enquiries','Logo artwork coordination','Quantity and sizing discussions','Quotation based on your brief'], 'kind':'detail'},
 '/diaries-asset-tags/': {'title':'Useful things, with your name on them.', 'eyebrow':'DIARIES & ASSET TAGS', 'intro':'Branded diaries, stationery and asset tags for your organisation.', 'image':'/images/photography/stationery.webp', 'items':['Branded diaries','Branded stationery','Asset tags','Organisation and identification materials','Bulk quotation enquiries'], 'kind':'detail'},
}

CSS = r'''@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&family=Manrope:wght@400;500;600;700;800&display=swap');
:root{--navy:#10243d;--blue:#183f67;--pale:#eaf1f8;--paper:#f5f8fc;--muted:#65768a;--line:#dbe4ed;--white:#fff;--shadow:0 22px 70px rgba(16,36,61,.12)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--navy);font-family:'DM Sans',sans-serif;line-height:1.6}a{color:inherit;text-decoration:none}img{max-width:100%;display:block}button,input,select,textarea{font:inherit}.wrap{width:min(1240px,calc(100% - 48px));margin-inline:auto}.topline{background:var(--navy);color:#d8e8f6;font-size:12px;padding:8px 0}.topline .wrap{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap}.header{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.94);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}.navrow{min-height:86px;display:flex;align-items:center;justify-content:space-between;gap:22px}.brand{display:flex;align-items:center;gap:11px;flex-shrink:0}.brand-mark{display:grid;place-items:center;width:43px;height:43px;border-radius:13px;background:var(--navy);color:white;font:800 22px Manrope,sans-serif}.brand-name{font:800 15px Manrope,sans-serif;letter-spacing:.16em;line-height:1.2}.brand-sub{display:block;color:var(--muted);font:700 9px 'DM Sans',sans-serif;letter-spacing:.25em;text-transform:uppercase;margin-top:4px}.navlinks{display:flex;align-items:center;gap:21px;font-size:12px;font-weight:700}.navlinks a{padding:8px 0;border-bottom:2px solid transparent}.navlinks a:hover,.navlinks a[aria-current=page]{border-color:var(--blue)}.btn{display:inline-flex;align-items:center;justify-content:center;gap:10px;border:1px solid transparent;border-radius:999px;padding:14px 21px;font-size:13px;font-weight:800;transition:transform .2s,background .2s;cursor:pointer}.btn:hover{transform:translateY(-2px)}.btn-primary{background:var(--navy);color:white}.btn-primary:hover{background:var(--blue)}.btn-light{background:white;border-color:var(--line)}.btn-blue{background:var(--blue);color:white}.nav-actions{display:flex;gap:10px;align-items:center}.menu-btn{display:none;border:1px solid var(--line);background:white;border-radius:12px;width:44px;height:44px;font-size:20px}.hero{padding:66px 0 74px;overflow:hidden;background:linear-gradient(105deg,var(--paper) 0%,var(--paper) 48%,#e4edf6 48%,#e4edf6 100%)}.hero-grid{display:grid;grid-template-columns:.95fr 1.05fr;gap:58px;align-items:center}.eyebrow{display:flex;align-items:center;gap:10px;color:var(--blue);font-size:10px;font-weight:800;letter-spacing:.2em;text-transform:uppercase}.eyebrow:before{content:'';width:27px;height:2px;background:currentColor}.hero h1{font:800 clamp(46px,6.8vw,90px)/.96 Manrope,sans-serif;letter-spacing:-.075em;margin:24px 0}.hero h1 span{color:var(--blue)}.lead{max-width:510px;font-size:17px;line-height:1.8;color:#52677e}.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}.hero-visual{position:relative;min-width:0}.hero-visual img{width:100%;height:470px;object-fit:contain;border-radius:30px;box-shadow:var(--shadow)}.floating-note{position:absolute;left:-24px;top:30px;background:#fff;border:1px solid #fff;border-radius:15px;padding:15px 18px;box-shadow:var(--shadow);font-size:12px;font-weight:800}.visual-caption{position:absolute;bottom:18px;left:18px;right:18px;background:rgba(16,36,61,.84);color:#fff;border-radius:16px;padding:17px 20px;font:700 19px Manrope,sans-serif;backdrop-filter:blur(8px)}.strip{background:white;border-block:1px solid var(--line)}.strip-grid{display:grid;grid-template-columns:repeat(4,1fr)}.strip-item{padding:24px 18px;border-right:1px solid var(--line)}.strip-item:last-child{border:0}.strip-item b{display:block;font:800 23px Manrope,sans-serif;color:var(--blue)}.strip-item span{display:block;color:var(--muted);font-size:12px;margin-top:3px}.section{padding:82px 0}.section.white{background:#fff}.section.dark{background:var(--navy);color:white}.section-head{display:flex;align-items:end;justify-content:space-between;gap:30px;margin-bottom:32px}.section h2,.section-head h2{font:800 clamp(30px,4.2vw,52px)/1.08 Manrope,sans-serif;letter-spacing:-.055em;margin:12px 0}.section-head p{max-width:420px;color:var(--muted);margin:0}.cards{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}.card{border:1px solid var(--line);background:white;border-radius:23px;overflow:hidden;transition:transform .25s,box-shadow .25s}.card:hover{transform:translateY(-5px);box-shadow:var(--shadow)}.card img{width:100%;height:250px;object-fit:contain;background:var(--pale)}.card-body{padding:22px}.card-body h3{font:800 20px Manrope,sans-serif;margin:0 0 8px}.card-body p{color:var(--muted);font-size:14px;line-height:1.7;margin:0 0 16px}.link{display:inline-flex;align-items:center;gap:8px;color:var(--blue);font-size:13px;font-weight:800}.link:after{content:'↗';font-size:17px}.service-panel{display:grid;grid-template-columns:1fr 1fr;gap:24px}.service-feature{position:relative;min-height:360px;border-radius:25px;overflow:hidden;background:var(--navy)}.service-feature img{position:absolute;width:100%;height:100%;object-fit:cover;opacity:.76}.service-feature:after{content:'';position:absolute;inset:0;pointer-events:none;background:linear-gradient(0deg,rgba(16,36,61,.95),transparent 75%)}.service-feature div{position:absolute;z-index:1;left:25px;right:25px;bottom:24px;color:white}.service-feature h3{font:800 27px Manrope,sans-serif;margin:0 0 8px}.service-feature p{max-width:400px;color:#e0e9f2;margin:0 0 15px;font-size:14px}.cta-band{background:#dce8f4;border-radius:28px;padding:36px;display:flex;align-items:center;justify-content:space-between;gap:22px}.cta-band h2{font:800 clamp(27px,3.5vw,42px)/1.12 Manrope,sans-serif;margin:10px 0}.page-hero{padding:58px 0 55px;background:linear-gradient(115deg,#f5f8fc 0%,#f5f8fc 55%,#e4edf6 55%)}.page-hero-grid{display:grid;grid-template-columns:1fr .8fr;align-items:center;gap:52px}.page-hero h1{font:800 clamp(38px,5vw,66px)/1.04 Manrope,sans-serif;letter-spacing:-.06em;margin:17px 0}.page-hero p{font-size:16px;color:#53677d;max-width:620px;line-height:1.85}.page-hero img{height:300px;width:100%;object-fit:contain;border-radius:24px;box-shadow:var(--shadow)}.detail-grid{display:grid;grid-template-columns:.8fr 1.2fr;gap:45px;align-items:start}.check-list{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.check-item{padding:17px;border:1px solid var(--line);border-radius:15px;background:white;font-size:13px;font-weight:700;display:flex;gap:11px;align-items:flex-start}.check-item:before{content:'✓';display:grid;place-items:center;flex-shrink:0;width:24px;height:24px;background:var(--pale);color:var(--blue);border-radius:50%;font-weight:900}.form-layout{display:grid;grid-template-columns:.75fr 1.25fr;gap:44px}.contact-list{display:grid;gap:18px;margin-top:28px}.contact-item{display:flex;align-items:center;gap:14px}.contact-icon{width:46px;height:46px;border-radius:15px;display:grid;place-items:center;background:var(--pale);font-size:19px}.contact-item small{display:block;color:var(--muted);font-size:11px}.contact-item b{font-size:14px;overflow-wrap:anywhere}.quote-form{background:white;border:1px solid var(--line);border-radius:24px;padding:28px;box-shadow:var(--shadow)}.quote-form h2{font:800 26px Manrope,sans-serif;margin:0 0 6px}.quote-form>p{color:var(--muted);font-size:13px;margin:0 0 22px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.field{display:grid;gap:7px;font-size:12px;font-weight:800}.field.full{grid-column:1/-1}.field input,.field select,.field textarea{width:100%;border:1px solid #ccd8e5;border-radius:11px;padding:12px 13px;background:#fff;color:var(--navy);outline:none}.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--blue);box-shadow:0 0 0 3px #183f671a}.field textarea{resize:vertical;min-height:110px}.form-status{margin-top:15px;padding:13px 15px;background:var(--pale);border-radius:12px;font-size:13px;color:var(--navy)}.footer{background:var(--navy);color:white;padding:52px 0 20px}.footer-grid{display:grid;grid-template-columns:1.2fr .8fr .8fr 1fr;gap:30px;padding-bottom:35px;border-bottom:1px solid #ffffff24}.footer h3{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#c7d9eb}.footer a,.footer p{font-size:13px;color:#d5dfeb}.footer-links{display:grid;gap:10px}.footer-bottom{display:flex;justify-content:space-between;gap:12px;padding-top:17px;color:#aebdce;font-size:11px}.whatsapp{position:fixed;z-index:30;bottom:20px;right:20px;background:#183f67;color:#fff;border-radius:999px;padding:13px 18px;box-shadow:var(--shadow);font-size:13px;font-weight:800}.mockup-label{display:inline-block;border-radius:999px;background:var(--pale);padding:7px 12px;color:var(--blue);font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.catalogue-callout{display:flex;align-items:center;justify-content:space-between;gap:20px;background:white;border:1px solid var(--line);border-radius:18px;padding:20px;margin-top:25px}.catalogue-callout strong{font:800 17px Manrope,sans-serif}.catalogue-callout p{margin:5px 0 0;font-size:13px;color:var(--muted)}.mobile-nav{display:none}
@media(max-width:1100px){.navlinks{gap:12px;font-size:11px}.nav-actions .catalogue-btn{display:none}.nav-actions .quote-btn{padding:12px 15px}.hero-grid{gap:30px}.hero-visual img{height:420px}}
@media(max-width:900px){.wrap{width:min(100% - 36px,700px)}.navrow{min-height:74px}.navlinks{display:none}.nav-actions .quote-btn{display:none}.menu-btn{display:block}.mobile-nav.open{display:grid;padding:0 18px 16px;gap:4px}.mobile-nav a{padding:11px 12px;border-radius:10px;font-size:13px;font-weight:700}.mobile-nav a:hover{background:var(--pale)}.hero{padding:42px 0 54px;background:linear-gradient(160deg,var(--paper) 0%,var(--paper) 60%,#e4edf6 60%)}.hero-grid,.page-hero-grid,.detail-grid,.form-layout{grid-template-columns:1fr}.hero-grid{gap:34px}.hero-visual img{height:360px}.floating-note{left:12px;top:12px}.strip-grid{grid-template-columns:repeat(2,1fr)}.strip-item:nth-child(2){border-right:0}.strip-item:nth-child(-n+2){border-bottom:1px solid var(--line)}.section{padding:60px 0}.section-head{align-items:start;flex-direction:column}.cards{grid-template-columns:repeat(2,1fr)}.service-panel{grid-template-columns:1fr 1fr}.page-hero{padding:42px 0}.page-hero-grid{gap:24px}.page-hero img{height:280px}.footer-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:600px){.wrap{width:calc(100% - 30px)}.topline .wrap{justify-content:center;text-align:center}.hero h1{font-size:clamp(46px,14vw,72px)}.hero-visual img{height:300px;border-radius:20px}.visual-caption{font-size:16px}.cards,.service-panel,.check-list,.form-grid{grid-template-columns:1fr}.card img{height:220px}.service-feature{min-height:320px}.cta-band{align-items:flex-start;flex-direction:column;padding:25px}.page-hero h1{font-size:39px}.page-hero img{height:230px}.quote-form{padding:19px}.field.full{grid-column:auto}.footer-grid{grid-template-columns:1fr;gap:25px}.footer-bottom{flex-direction:column}.whatsapp{right:12px;bottom:12px;padding:12px 14px}.catalogue-callout{align-items:flex-start;flex-direction:column}}
html{scroll-padding-top:100px}
main[id]{scroll-margin-top:100px}
:focus-visible{outline:3px solid #3975a8;outline-offset:4px}
.skip-link{position:fixed;z-index:100;top:12px;left:12px;transform:translateY(-160%);padding:12px 16px;border-radius:10px;background:#fff;color:var(--navy);font-weight:800;box-shadow:var(--shadow)}
.skip-link:focus{transform:translateY(0)}
.mobile-nav{max-height:calc(100vh - 74px);overflow-y:auto}
.mobile-nav a[aria-current=page]{background:var(--pale);color:var(--blue)}
.btn:focus-visible,.menu-btn:focus-visible,.whatsapp:focus-visible{outline-offset:3px}
@media(max-width:600px){.hero{padding-top:34px}.hero-grid{gap:27px}.strip-item{padding:19px 14px}.strip-item b{font-size:20px}.section{padding:50px 0}.page-hero{padding:34px 0}.actions .btn{flex:1 1 auto}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{scroll-behavior:auto!important;transition-duration:.01ms!important;animation-duration:.01ms!important;animation-iteration-count:1!important}}
:root{--navy:#183c35;--blue:#47735f;--pale:#e8eee6;--paper:#f6f4ee;--muted:#64736b;--line:#dce3da;--white:#fff;--gold:#b8894f;--shadow:0 26px 72px rgba(24,60,53,.14)}
body{background:var(--paper);color:#203b34}
.topline{background:#14332d;color:#e8eee6}
.header{background:rgba(250,249,245,.94);box-shadow:0 8px 32px rgba(24,60,53,.055)}
.brand-mark{background:linear-gradient(145deg,#214b40,#102c26);box-shadow:inset 0 1px 0 #ffffff30,0 8px 20px #17392c25}
.navlinks a:hover,.navlinks a[aria-current=page]{border-color:var(--gold)}
.btn{border-radius:10px;padding:14px 20px;box-shadow:0 7px 18px rgba(24,60,53,.08)}
.btn-primary{background:linear-gradient(135deg,#245644,#153c32);box-shadow:0 9px 20px rgba(24,60,53,.2),inset 0 1px 0 #ffffff25}
.btn-primary:hover{background:linear-gradient(135deg,#326b54,#1b493c);box-shadow:0 13px 26px rgba(24,60,53,.24)}
.btn-light{background:#fffefa;border-color:#d8dfd5}
.menu-btn{border-radius:10px}
.hero{position:relative;isolation:isolate;padding:84px 0 86px;background:radial-gradient(ellipse at 87% 37%,rgba(222,232,218,.95),transparent 39%),linear-gradient(108deg,#f7f5ef 0%,#f7f5ef 52%,#edf0e8 52%,#edf0e8 100%)}
.hero:before{content:"";position:absolute;z-index:-1;width:360px;height:360px;right:-155px;top:-145px;border:1px solid rgba(184,137,79,.24);border-radius:50%;box-shadow:0 0 0 30px rgba(255,255,255,.18),0 0 0 60px rgba(255,255,255,.12)}
.hero-grid{grid-template-columns:1fr 1.02fr;gap:clamp(38px,6vw,86px)}
.eyebrow{color:#547760;letter-spacing:.18em}
.eyebrow:before{width:30px;height:2px;color:var(--gold);background:var(--gold)}
.hero h1{font-size:clamp(49px,6.2vw,82px);letter-spacing:-.07em;line-height:.99;margin:25px 0 21px}
.hero h1 span{color:#4e775f}
.lead{max-width:490px;color:#5e6f66;font-size:17px;line-height:1.8}
.hero .actions{margin-top:30px}
.hero-visual{perspective:1400px;transform-style:preserve-3d}
.hero-visual:before{content:"";position:absolute;z-index:-1;inset:17px -17px -15px 17px;border:1px solid rgba(184,137,79,.5);border-radius:30px;transform:rotate(2.5deg) translateZ(-28px)}
.hero-visual img{height:500px;border-radius:25px;transform:rotateY(-4deg) rotateX(1.5deg) translateZ(10px);box-shadow:0 38px 80px rgba(21,49,41,.23),0 12px 26px rgba(21,49,41,.14);transition:transform .55s cubic-bezier(.2,.7,.2,1),box-shadow .55s}
.hero-visual:hover img{transform:rotateY(-1deg) rotateX(0) translateY(-5px) translateZ(16px);box-shadow:0 48px 95px rgba(21,49,41,.27),0 14px 30px rgba(21,49,41,.16)}
.floating-note{left:-30px;top:28px;border:1px solid #ffffffcf;border-radius:12px;color:#244438;box-shadow:0 16px 35px rgba(21,49,41,.16);letter-spacing:.035em}
.visual-caption{background:linear-gradient(105deg,rgba(19,48,41,.93),rgba(32,71,57,.8));border:1px solid #ffffff2c;border-radius:13px;box-shadow:0 8px 25px #09251f40}
.mockup-label{background:#e7eee5;color:#426650;letter-spacing:.1em}
.strip{background:#fffefa;border-color:var(--line)}
.strip-item{position:relative;padding-block:25px}
.strip-item b{color:#b8894f;font-size:21px}
.strip-item span{color:#52665d;font-size:12px;font-weight:700;letter-spacing:.015em}
.section{padding:88px 0}
.section h2,.section-head h2{letter-spacing:-.045em}
.section-head p{color:#66746c;line-height:1.8}
.section.dark{background:radial-gradient(ellipse at 87% 15%,#2a5749 0%,transparent 40%),#173a32}
.section.dark .eyebrow{color:#d6c09a}
.section.dark .eyebrow:before{background:#c39a63}
.section.dark .section-head p{color:#d1ded4}
.card{border-color:#e5e6dd;border-radius:16px;background:#fffefa;box-shadow:0 8px 25px rgba(29,55,46,.045);transition:transform .35s cubic-bezier(.2,.7,.2,1),box-shadow .35s,border-color .35s}
.card:hover{transform:translateY(-8px) rotateX(1deg);border-color:#c8d4c9;box-shadow:0 24px 48px rgba(29,55,46,.14)}
.card img{height:260px;object-fit:contain;transition:transform .55s cubic-bezier(.2,.7,.2,1)}
.card:hover img{transform:scale(1.035)}
.card-body{padding:23px}
.card-body h3{color:#213e34}
.card-body p{color:#65736b}
.link{color:#47735f}
.link:after{color:var(--gold)}
.service-feature{min-height:385px;border-radius:18px;box-shadow:0 20px 45px rgba(3,19,15,.25);transition:transform .4s,box-shadow .4s}
.service-feature:hover{transform:translateY(-7px) rotateX(1deg);box-shadow:0 30px 60px rgba(3,19,15,.34)}
.service-feature img{transition:transform .6s}
.service-feature:hover img{transform:scale(1.04)}
.service-feature:after{background:linear-gradient(0deg,rgba(13,38,31,.97),rgba(13,38,31,.03) 82%)}
.cta-band{position:relative;overflow:hidden;background:linear-gradient(120deg,#e6ece2,#f2ebdd);border:1px solid #e2e4d9;border-radius:18px;box-shadow:0 18px 45px rgba(34,66,54,.08)}
.cta-band:after{content:"";position:absolute;width:210px;height:210px;right:13%;top:-150px;border:1px solid rgba(184,137,79,.4);border-radius:50%;box-shadow:0 0 0 20px rgba(255,255,255,.13),0 0 0 40px rgba(255,255,255,.1);pointer-events:none}
.page-hero{background:radial-gradient(ellipse at 90% 35%,rgba(218,229,215,.95),transparent 36%),linear-gradient(110deg,#f7f5ef 0%,#f7f5ef 56%,#edf0e8 56%,#edf0e8 100%)}
.page-hero h1{color:#1d3d33;letter-spacing:-.055em}
.page-hero p{color:#5e6f66;line-height:1.8}
.page-hero img{border-radius:18px;box-shadow:0 28px 65px rgba(21,49,41,.2),0 8px 20px rgba(21,49,41,.1);transform:rotateY(-3deg);transition:transform .45s}
.page-hero img:hover{transform:rotateY(0) translateY(-4px)}
.detail-grid{gap:55px}
.check-item{background:#fffefa;border-color:#e0e5dd;border-radius:13px;color:#29463b}
.check-item:before{background:#e7eee5;color:#46705a}
.quote-form{background:#fffefa;border-color:#e0e5dd;border-radius:18px;box-shadow:0 22px 55px rgba(26,55,45,.1)}
.field input,.field select,.field textarea{border-color:#d6ded5;border-radius:9px}
.field input:focus,.field select:focus,.field textarea:focus{border-color:#5b8067;box-shadow:0 0 0 3px #47735f20}
.form-status{background:#e7eee5;color:#244438}
.footer{background:radial-gradient(ellipse at 78% 0%,#285344 0%,transparent 39%),#15362f}
.footer .brand-mark{background:#f7f4eb!important;color:#183c35!important}
.footer h3{color:#dac8a7}
.whatsapp{background:#285d48;border:1px solid #ffffff22;border-radius:10px;box-shadow:0 10px 26px rgba(13,38,30,.24)}
.whatsapp:hover{background:#347255;transform:translateY(-3px)}
.catalogue-callout{background:#fffefa;border-color:#e1e5dc;border-radius:14px}
.photo-credit{display:block;margin:0 0 12px;color:#788279;font-size:10px;line-height:1.6}
.photo-credit a{color:inherit;text-decoration:underline;text-underline-offset:2px}
.catalog-item-note{margin-top:16px;color:var(--muted);font-size:12px}
@media(max-width:900px){.hero{background:radial-gradient(ellipse at 88% 72%,#e1e9df,transparent 40%),#f7f5ef}.hero:before{right:-230px}.hero-visual img{height:390px}.hero-visual:before{inset:13px -10px -12px 12px}.page-hero{background:radial-gradient(ellipse at 90% 75%,#e1e9df,transparent 38%),#f7f5ef}.page-hero img{transform:none}.page-hero img:hover{transform:translateY(-3px)}}
@media(max-width:900px){.hero-grid{grid-template-columns:1fr}.hero-visual{max-width:680px;width:100%;margin-inline:auto}.hero-visual img{transform:none}}
@media(max-width:600px){.hero{padding-top:39px;padding-bottom:48px}.hero h1{font-size:clamp(45px,12.5vw,67px);line-height:1.02}.hero-visual img{height:290px;border-radius:17px;transform:none}.hero-visual:hover img{transform:translateY(-3px)}.hero-visual:before{inset:10px -7px -10px 8px;border-radius:19px}.floating-note{left:10px;top:10px;padding:11px 13px;font-size:10px}.visual-caption{left:12px;right:12px;bottom:12px;padding:13px 15px}.section{padding:55px 0}.card img{height:225px}.service-feature{border-radius:15px}.cta-band{border-radius:15px}.page-hero img{border-radius:15px}.strip-item{padding:18px 12px}.strip-item b{font-size:18px}.actions .btn{flex:1 1 auto}}
.service-panel.premium-services{grid-template-columns:repeat(3,minmax(0,1fr))}
.service-panel.premium-services .service-feature{min-height:340px}
@media(max-width:900px){.service-panel.premium-services{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.service-panel.premium-services{grid-template-columns:1fr}.service-panel.premium-services .service-feature{min-height:300px}}
.upload-shell{padding:64px 0 80px;background:linear-gradient(145deg,#f7f5ef,#e9eee7)}
.upload-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(290px,.75fr);gap:32px;align-items:start}
.upload-card,.qr-card{background:#fffefa;border:1px solid #e0e5dd;border-radius:20px;padding:clamp(22px,4vw,42px);box-shadow:0 20px 55px rgba(26,55,45,.08)}
.upload-card h1,.qr-card h1{font:800 clamp(35px,5vw,54px)/1.05 Manrope,sans-serif;letter-spacing:-.06em;margin:0 0 14px}
.upload-card>p,.qr-card>p{color:var(--muted)}
.upload-card .field{margin-top:17px}
.upload-card [hidden]{display:none!important}
.upload-card input[type=file]{padding:13px;background:#fff}
.upload-note{font-size:12px;color:var(--muted)}
.upload-result{margin-top:18px;padding:16px;background:#e7eee5;border-radius:12px}
.upload-result[hidden]{display:none}
.qr-shell{padding:64px 0 80px}
.qr-card{max-width:760px;margin-inline:auto;text-align:center}
.qr-image{width:min(330px,80vw);aspect-ratio:1;margin:26px auto;object-fit:contain;padding:12px;border:1px solid var(--line);border-radius:12px}
.qr-actions{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}
.qr-instructions{max-width:540px;margin:0 auto 20px;color:var(--muted)}
@media(max-width:760px){.upload-shell,.qr-shell{padding:36px 0 55px}.upload-grid{grid-template-columns:1fr}}
@media print{.topline,.header,.footer,.whatsapp,.qr-actions,.skip-link{display:none!important}body,.qr-shell{background:#fff!important}.wrap{width:100%}.qr-card{border:0;box-shadow:none;padding:15mm}.qr-image{width:85mm;margin:12mm auto}.qr-card h1{font-size:28pt}}

/* A darker, photo-led identity inspired by the reference while keeping Esicom's own palette. */
.header{background:rgba(20,51,45,.97);border-bottom-color:#ffffff1c;box-shadow:0 12px 35px rgba(13,38,31,.18)}
.brand-name{color:#fff}
.brand-sub{color:#c5d7ca}
.brand-mark{background:#f7f5ef;color:#183c35;box-shadow:none}
.navlinks a{color:#edf4ed}
.navlinks a:hover,.navlinks a[aria-current=page]{border-color:#69b875;color:#fff}
.header .btn-light{background:transparent;border-color:#ffffff55;color:#fff;box-shadow:none}
.header .btn-primary{background:#2f9b55;color:#fff;box-shadow:0 8px 22px rgba(24,111,58,.28)}
.header .btn-primary:hover{background:#38ad63}
.menu-btn{background:transparent;border-color:#ffffff55;color:#fff}
.mobile-nav{background:#14332d;border-top-color:#ffffff20}
.mobile-nav a{color:#edf4ed}
.mobile-nav a:hover,.mobile-nav a[aria-current=page]{background:#ffffff12;color:#fff}
.hero{padding:88px 0 92px;background:radial-gradient(ellipse at 90% 32%,rgba(218,231,216,.88),transparent 42%),linear-gradient(112deg,#f8f7f2 0%,#f8f7f2 50%,#eaf0e8 50%,#eaf0e8 100%)}
.hero h1{max-width:650px;font-size:clamp(52px,6.4vw,88px);line-height:.98}
.hero h1 span{color:#347d4a}
.hero-visual img{height:520px;border-radius:20px;transform:none;box-shadow:0 34px 72px rgba(21,49,41,.22)}
.hero-visual:hover img{transform:translateY(-5px);box-shadow:0 42px 85px rgba(21,49,41,.27)}
.hero-visual:before{border-radius:22px}
.visual-caption{background:linear-gradient(105deg,rgba(18,48,39,.94),rgba(34,80,52,.82))}
.btn-primary{background:#267a46}
.btn-primary:hover{background:#338b52}
.section-head h2{color:#1d3d33}
.section.dark .section-head h2{color:#fff}
.service-feature{min-height:390px}
.cta-band{background:linear-gradient(120deg,#e3ebdf,#f0e8d8);border-color:#dce3d8}
.footer{background:radial-gradient(ellipse at 78% 0%,#285344 0%,transparent 39%),#14332d}
.whatsapp{background:#218c4c}
.whatsapp:hover{background:#2ba45a}
@media(max-width:900px){
  .hero{padding:62px 0 66px;background:radial-gradient(ellipse at 88% 72%,#e1e9df,transparent 40%),#f7f5ef}
  .hero-visual img{height:420px}
}
@media(max-width:600px){
  .hero{padding:40px 0 50px}
  .hero h1{font-size:clamp(46px,12vw,68px)}
  .hero-visual img{height:290px}
}
.hero-visual{min-width:0}
.hero-carousel{position:relative;overflow:hidden;border-radius:22px;background:#173a32;box-shadow:0 34px 72px rgba(21,49,41,.22)}
.hero-slide-link{display:block;position:relative}
.hero-carousel img{height:520px;width:100%;object-fit:contain;opacity:1;transition:opacity .35s ease,transform .8s cubic-bezier(.2,.7,.2,1)}
.hero-carousel img.is-changing{opacity:.35;transform:scale(1.025)}
.hero-slide-link:after{content:"";position:absolute;inset:30% 0 0;background:linear-gradient(0deg,rgba(13,38,31,.78),transparent);pointer-events:none}
.hero-carousel .visual-caption{position:absolute;z-index:1;left:22px;right:22px;bottom:20px;display:flex;align-items:end;justify-content:space-between;gap:18px;background:transparent;border:0;box-shadow:none;padding:0}
.hero-caption-copy{display:grid;gap:4px}
.hero-caption-copy small{font-size:10px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:#d8c49f}
.hero-caption-copy strong{font:800 clamp(18px,2.2vw,25px)/1.15 Manrope,sans-serif;color:#fff}
.hero-slide-more{flex:0 0 auto;color:#fff;font-size:12px;font-weight:800}
.hero-carousel-controls{position:absolute;z-index:2;top:18px;right:18px;display:flex;align-items:center;gap:7px;padding:7px;border:1px solid #ffffff42;border-radius:999px;background:rgba(19,48,41,.7);backdrop-filter:blur(12px)}
.hero-carousel-controls button{display:grid;place-items:center;min-width:32px;height:32px;padding:0 9px;border:0;border-radius:999px;background:transparent;color:#fff;font:700 13px 'DM Sans',sans-serif;cursor:pointer}
.hero-carousel-controls button:hover,.hero-carousel-controls button:focus-visible{background:#ffffff24;outline:none}
.hero-carousel-controls [data-hero-dots]{display:flex;align-items:center;gap:5px}
.hero-carousel-controls [data-hero-dots] button{min-width:10px;width:10px;height:10px;padding:0;background:#ffffff75}
.hero-carousel-controls [data-hero-dots] button[aria-current=true]{width:24px;background:#d8c49f}
.hero-carousel .floating-note{z-index:2;top:20px;left:20px;border-radius:999px;padding:11px 15px;background:#fffefa;color:#244438}
.hero-carousel:before{display:none}
@media(max-width:900px){.hero-carousel img{height:420px}}
@media(max-width:600px){
 .hero-carousel{border-radius:16px}
 .hero-carousel img{height:300px}
 .hero-carousel .floating-note{top:13px;left:12px;padding:9px 12px}
 .hero-carousel-controls{top:12px;right:12px;gap:3px;padding:5px}
 .hero-carousel-controls button{min-width:28px;height:28px}
 .hero-carousel .visual-caption{left:14px;right:14px;bottom:14px}
 .hero-caption-copy strong{font-size:18px}
}
body.visual-editor-mode img,
body.visual-editor-mode h1,
body.visual-editor-mode h2,
body.visual-editor-mode h3,
body.visual-editor-mode p,
body.visual-editor-mode a,
body.visual-editor-mode button,
body.visual-editor-mode span,
body.visual-editor-mode small,
body.visual-editor-mode li,
body.visual-editor-mode .eyebrow,
body.visual-editor-mode .mockup-label{cursor:crosshair!important}
body.visual-editor-mode img:hover,
body.visual-editor-mode h1:hover,
body.visual-editor-mode h2:hover,
body.visual-editor-mode h3:hover,
body.visual-editor-mode p:hover,
body.visual-editor-mode a:hover,
body.visual-editor-mode button:hover,
body.visual-editor-mode span:hover,
body.visual-editor-mode small:hover,
body.visual-editor-mode li:hover,
body.visual-editor-mode .eyebrow:hover,
body.visual-editor-mode .mockup-label:hover,
body.visual-editor-mode .visual-editor-selected{outline:3px solid #b8894f!important;outline-offset:3px}
.cards[data-featured-products] .card img{height:300px}
.cards[data-featured-products] .card{border-radius:18px}
.editable-section{background:#fffefa}
.editable-section-card{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:36px;align-items:center}
.editable-section-card>img{width:100%;max-height:440px;object-fit:contain;border-radius:18px}
.editable-section-copy h2{font:800 clamp(29px,4vw,45px)/1.1 Manrope,sans-serif;letter-spacing:-.05em;margin:0 0 14px;color:#1d3d33}
.editable-section-copy p{color:var(--muted);line-height:1.85;white-space:pre-line;margin:0 0 20px}
@media(max-width:700px){.editable-section-card{grid-template-columns:1fr;gap:22px}}
@media(prefers-reduced-motion:reduce){.hero-carousel img{transition:none}}

/* Premium dimensional layer shared by every public page. */
body{background-image:radial-gradient(ellipse at 4% 12%,rgba(219,230,216,.42),transparent 28%),radial-gradient(ellipse at 96% 48%,rgba(232,222,202,.26),transparent 26%);background-attachment:fixed}
.header{box-shadow:0 14px 38px rgba(13,38,31,.22)}
.brand-mark{transform:perspective(260px) rotateY(-10deg);box-shadow:inset 0 1px 0 #ffffffb0,0 9px 18px #071f1838}
.navlinks a{transition:color .2s,border-color .2s,transform .2s}
.navlinks a:hover{transform:translateY(-2px)}
.hero-visual,.page-hero-grid>img{transform-style:preserve-3d}
.hero-visual img,.page-hero-grid>img{object-fit:cover;border:1px solid #ffffffc9;backface-visibility:hidden}
.hero-visual img{transform:perspective(1300px) rotateY(-4deg) rotateX(1.5deg) translateZ(10px)}
.hero-visual:hover img{transform:perspective(1300px) rotateY(-1deg) rotateX(0) translateY(-6px) translateZ(20px)}
.page-hero-grid>img{transform:perspective(1100px) rotateY(-5deg) rotateX(1.5deg) translateZ(10px);box-shadow:0 34px 70px rgba(21,49,41,.23),0 9px 22px rgba(21,49,41,.12)}
.page-hero-grid>img:hover{transform:perspective(1100px) rotateY(-1deg) translateY(-5px) translateZ(16px)}
.card,.service-feature,.quote-form,.upload-card,.qr-card,.cta-band{transform-style:preserve-3d;backface-visibility:hidden}
.card{perspective:1000px}
.card:hover{transform:perspective(1000px) translateY(-8px) rotateX(2deg) rotateY(-.5deg);box-shadow:0 28px 52px rgba(29,55,46,.17),0 5px 12px rgba(29,55,46,.07)}
.card img{object-fit:cover}
.service-feature:hover{transform:perspective(1000px) translateY(-8px) rotateX(1.5deg) rotateY(-.5deg)}
.strip-item{transition:background .25s,transform .25s,box-shadow .25s}
.strip-item:hover{z-index:1;transform:perspective(600px) translateY(-4px) rotateX(3deg);background:#fffefa;box-shadow:0 15px 28px rgba(29,55,46,.1)}
.check-item{transition:transform .22s,box-shadow .22s,border-color .22s}
.check-item:hover{transform:perspective(650px) translateY(-3px) rotateX(2deg);border-color:#c9d7c9;box-shadow:0 12px 22px rgba(29,55,46,.08)}
.quote-form,.upload-card,.qr-card{box-shadow:0 28px 65px rgba(26,55,45,.12),0 4px 12px rgba(26,55,45,.04);transition:transform .35s,box-shadow .35s,border-color .35s}
.quote-form:hover,.upload-card:hover,.qr-card:hover{transform:perspective(1200px) translateY(-4px) rotateX(.6deg);border-color:#ced9cc;box-shadow:0 35px 76px rgba(26,55,45,.16),0 8px 18px rgba(26,55,45,.06)}
.field input,.field select,.field textarea{box-shadow:inset 0 1px 2px rgba(24,60,53,.035);transition:border-color .18s,box-shadow .18s,background .18s}
.field input:hover,.field select:hover,.field textarea:hover{border-color:#aebfae;background:#fff}
.qr-image{transform:perspective(700px) rotateX(2deg);box-shadow:0 18px 36px rgba(24,60,53,.12);background:#fff}
.cta-band{transition:transform .3s,box-shadow .3s}
.cta-band:hover{transform:perspective(900px) translateY(-4px) rotateX(1deg);box-shadow:0 25px 55px rgba(34,66,54,.14)}
.btn{transition:transform .2s,background .2s,box-shadow .2s}
.btn:active{transform:translateY(1px) scale(.985)}
.footer{border-top:1px solid #ffffff22}
@media(max-width:900px){.hero-visual img,.page-hero-grid>img,.hero-visual:hover img,.page-hero-grid>img:hover{transform:none}}
@media(max-width:600px){body{background-attachment:scroll}.card:hover,.service-feature:hover,.quote-form:hover,.upload-card:hover,.qr-card:hover,.cta-band:hover,.strip-item:hover,.check-item:hover{transform:translateY(-2px)}.hero-visual img,.page-hero-grid>img{object-fit:cover}.hero-visual img{height:290px}}
@media(prefers-reduced-motion:reduce){.hero-visual img,.page-hero-grid>img,.card,.service-feature,.quote-form,.upload-card,.qr-card,.cta-band,.strip-item,.check-item{transition:none!important}.card:hover,.service-feature:hover,.quote-form:hover,.upload-card:hover,.qr-card:hover,.cta-band:hover,.strip-item:hover,.check-item:hover{transform:none}}

/* Make the dimensional art direction visible before the visitor interacts. */
.hero-visual img{transform:perspective(1050px) rotateY(-8deg) rotateX(3deg) translateZ(18px);box-shadow:22px 30px 0 -18px rgba(184,137,79,.72),0 48px 90px rgba(13,38,31,.28),0 14px 28px rgba(13,38,31,.16)}
.hero-visual:hover img{transform:perspective(1050px) rotateY(-2deg) rotateX(1deg) translateY(-10px) translateZ(30px);box-shadow:16px 24px 0 -18px rgba(184,137,79,.82),0 58px 105px rgba(13,38,31,.34),0 18px 32px rgba(13,38,31,.19)}
.page-hero-grid>img{transform:perspective(950px) rotateY(-9deg) rotateX(3deg) translateZ(16px);box-shadow:24px 28px 0 -18px rgba(184,137,79,.72),0 42px 82px rgba(13,38,31,.27),0 12px 24px rgba(13,38,31,.15)}
.card{box-shadow:0 18px 0 -12px rgba(184,137,79,.38),0 20px 40px rgba(29,55,46,.13)}
.card:nth-child(3n+1){transform:perspective(1000px) rotateY(-2deg) rotateX(1deg) translateZ(7px)}
.card:nth-child(3n+2){transform:perspective(1000px) translateY(-4px) translateZ(18px)}
.card:nth-child(3n){transform:perspective(1000px) rotateY(2deg) rotateX(1deg) translateZ(7px)}
.card:hover{transform:perspective(1000px) translateY(-13px) rotateX(4deg) rotateY(-1deg) translateZ(24px);box-shadow:0 26px 0 -17px rgba(184,137,79,.68),0 38px 68px rgba(29,55,46,.23)}
.service-feature{transform:perspective(1000px) rotateY(-2deg) translateZ(8px);box-shadow:18px 24px 0 -18px rgba(184,137,79,.7),0 30px 55px rgba(3,19,15,.27)}
.service-feature:nth-child(even){transform:perspective(1000px) rotateY(2deg) translateZ(8px)}
.upload-grid>.upload-card:first-child{transform:perspective(1250px) rotateY(-3deg) rotateX(1deg) translateZ(12px)}
.upload-grid>.upload-card:nth-child(2){transform:perspective(1250px) rotateY(3deg) rotateX(1deg) translateZ(8px)}
.qr-card{transform:perspective(1100px) rotateX(2deg) translateZ(12px)}
.quote-form,.upload-card,.qr-card{box-shadow:16px 22px 0 -16px rgba(184,137,79,.62),0 32px 68px rgba(26,55,45,.18)}
@media(max-width:900px){.hero-visual img,.page-hero-grid>img{transform:perspective(1200px) rotateY(-4deg) rotateX(2deg) translateZ(8px)}}
@media(max-width:600px){.hero-visual img,.page-hero-grid>img,.card,.card:nth-child(3n+1),.card:nth-child(3n+2),.card:nth-child(3n),.service-feature,.service-feature:nth-child(even),.upload-grid>.upload-card:first-child,.upload-grid>.upload-card:nth-child(2),.qr-card{transform:none}.card:hover,.service-feature:hover,.quote-form:hover,.upload-card:hover,.qr-card:hover,.cta-band:hover{transform:translateY(-4px)}}
@media(prefers-reduced-motion:reduce){.hero-visual img,.page-hero-grid>img,.card,.service-feature,.upload-card,.qr-card{transform:none!important}.card:hover,.service-feature:hover,.quote-form:hover,.upload-card:hover,.qr-card:hover{transform:none!important}}

/* ESICOM editorial redesign: typography and composition, never fake depth. */
*,*::before,*::after{box-shadow:none!important;text-shadow:none!important;filter:none!important}
*,*::before,*::after{transform:none!important}
:root{--navy:#173a31;--blue:#355b49;--pale:#e6e9df;--paper:#f5f3ed;--muted:#68716a;--line:#d4d4ca;--white:#fffefb;--gold:#c59b62;--shadow:none}
html{scroll-behavior:smooth}
body{background:#f5f3ed!important;background-image:none!important;color:#20352e;font-family:'DM Sans',sans-serif;line-height:1.65}
.wrap{width:min(1320px,calc(100% - 64px))}
.topline{background:#173a31;color:#e7e9dd;letter-spacing:.11em;font-size:10px}
.topline a{color:#fffefb;text-decoration:underline;text-decoration-color:#c59b62;text-underline-offset:4px}
.header{background:#f5f3ed!important;border-bottom:1px solid #c9cbc0;backdrop-filter:none;}
.navrow{min-height:82px}
.brand-mark{width:38px;height:38px;border-radius:0;background:#173a31!important;color:#f5f3ed!important;font:700 19px 'Instrument Serif',Georgia,serif!important}
.brand-name{color:#173a31!important;font-size:14px;letter-spacing:.2em}
.brand-sub{color:#68716a!important;letter-spacing:.22em}
.navlinks{gap:clamp(12px,1.8vw,26px);font-size:11px;letter-spacing:.025em}
.navlinks a{color:#35483f!important;border-bottom:1px solid transparent;padding:10px 0}
.navlinks a:hover,.navlinks a[aria-current=page]{color:#173a31!important;border-color:#c59b62!important}
.btn,.header .btn{border-radius:2px!important;box-shadow:none!important;letter-spacing:.06em;text-transform:uppercase;font-size:10px;padding:14px 18px}
.btn-primary,.header .btn-primary{background:#173a31!important;color:#f5f3ed!important;border:1px solid #173a31!important}
.btn-primary:hover,.header .btn-primary:hover{background:#c59b62!important;border-color:#c59b62!important;color:#173a31!important}
.btn-light,.header .btn-light{background:transparent!important;color:#173a31!important;border:1px solid #aeb4a8!important}
.menu-btn{border-radius:2px!important;color:#173a31!important;border-color:#aeb4a8!important}
.mobile-nav{background:#f5f3ed!important;border-top:1px solid #d4d4ca}
.mobile-nav a{color:#173a31!important}
.hero{padding:clamp(68px,9vw,126px) 0 clamp(62px,8vw,105px);background:#f5f3ed!important;position:relative;isolation:isolate}
.hero:before{content:'NAIROBI  /  EST. WITH PURPOSE';display:block;position:absolute;left:50%;top:24px;width:min(1320px,calc(100% - 64px));transform:translateX(-50%)!important;border-bottom:1px solid #d4d4ca;padding-bottom:14px;color:#68716a;font:600 9px 'DM Sans',sans-serif;letter-spacing:.2em}
.hero:after{content:'ESICOM';position:absolute;z-index:-1;right:2vw;top:7%;color:#eeece4;font:400 clamp(90px,18vw,260px)/.8 'Instrument Serif',Georgia,serif;letter-spacing:-.055em;pointer-events:none}
.hero-grid{grid-template-columns:minmax(0,.88fr) minmax(0,1.12fr);gap:clamp(40px,8vw,120px);align-items:center}
.hero h1,.page-hero h1,.section h2,.section-head h2,.detail-grid h2,.quote-form h2,.upload-card h1,.qr-card h1{font-family:'Instrument Serif',Georgia,serif!important;font-weight:400!important;letter-spacing:-.035em!important;color:#173a31!important}
.hero h1{font-size:clamp(76px,10.5vw,148px)!important;line-height:.82!important;margin:30px 0 26px;max-width:650px}
.hero h1 span{color:#b7854e!important;font-style:italic}
.eyebrow{color:#647468!important;font-size:9px;letter-spacing:.22em;font-weight:700}
.eyebrow:before{background:#c59b62!important;width:34px}
.lead{max-width:430px;color:#596a60;font-size:16px;line-height:1.85}
.hero .actions{margin-top:34px}
.hero-visual{padding:0 16px 16px 0;position:relative}
.hero-visual:before{display:block!important;content:'';position:absolute;z-index:-1;inset:17px -1px -1px 17px;border:1px solid #c59b62;border-radius:0;transform:none!important}
.hero-visual img{height:clamp(390px,45vw,610px);object-fit:cover;border:0!important;border-radius:0!important;transform:none!important}
.floating-note{left:-19px;top:22px;border:0!important;border-radius:0!important;background:#173a31!important;color:#f5f3ed!important;padding:12px 15px;font-size:9px;letter-spacing:.16em;text-transform:uppercase}
.visual-caption{bottom:16px;left:16px;right:32px;border-radius:0!important;background:#173a31!important;color:#f5f3ed;padding:18px 20px;font:400 22px 'Instrument Serif',Georgia,serif!important;backdrop-filter:none}
.strip{background:#e9e9df!important;border-block:1px solid #d0d1c6}
.strip-grid{grid-template-columns:repeat(4,minmax(0,1fr))}
.strip-item{padding:21px 20px!important;border-right:1px solid #c9cbc0!important}
.strip-item b{color:#b7854e!important;font:400 29px 'Instrument Serif',Georgia,serif!important}
.strip-item span{color:#45574c!important;font-size:10px;text-transform:uppercase;letter-spacing:.12em}
.section{padding:clamp(68px,8vw,112px) 0}
.section.white{background:#fffefb!important}
.section.dark{background:#173a31!important;color:#f5f3ed}
.section.dark h2,.section.dark .section-head h2{color:#f5f3ed!important}
.section.dark .eyebrow{color:#d7c69f!important}
.section-head{border-bottom:1px solid #d4d4ca;padding-bottom:22px;margin-bottom:32px;align-items:end}
.section.dark .section-head{border-color:#ffffff38}
.section-head h2,.section h2{font-size:clamp(42px,6vw,78px)!important;line-height:.96!important;margin:12px 0!important}
.section-head p{font-size:13px;line-height:1.8;color:#68716a!important;max-width:390px}
.section.dark .section-head p{color:#d3d8ce!important}
.cards{gap:22px;align-items:start}
.card{background:transparent!important;border:0!important;border-bottom:1px solid #c9cbc0!important;border-radius:0!important;overflow:hidden}
.card:hover{border-color:#b7854e!important}
.card img{height:clamp(220px,24vw,330px)!important;object-fit:cover!important;background:#e9e9df!important;border-radius:0!important}
.card-body{padding:20px 2px 25px!important}
.card-body h3{font:400 29px/1.05 'Instrument Serif',Georgia,serif!important;color:#173a31!important;margin-bottom:10px!important}
.card-body p{font-size:12px!important;line-height:1.8!important;color:#68716a!important}
.link{color:#355b49!important;text-transform:uppercase;font-size:9px;letter-spacing:.12em}
.link:after{color:#b7854e!important}
.service-panel{gap:14px}
.service-feature,.service-panel.premium-services .service-feature{min-height:clamp(300px,32vw,440px)!important;border-radius:0!important;background:#173a31!important}
.service-feature img{opacity:.62!important;object-fit:cover;transform:none!important;transition:opacity .25s}
.service-feature:after{background:linear-gradient(0deg,rgba(12,40,32,.88),rgba(12,40,32,.02) 78%)!important}
.service-feature:hover img{opacity:.8!important}
.service-feature div{left:24px;right:24px;bottom:24px}
.service-feature h3{font:400 36px/1 'Instrument Serif',Georgia,serif!important}
.service-feature p{font-size:12px;color:#e2e5dc!important}
.cta-band{border-radius:0!important;background:#e8e8de!important;border:1px solid #d1d2c7!important;padding:clamp(26px,4vw,44px)!important}
.cta-band h2{font:400 clamp(38px,5vw,64px)/.95 'Instrument Serif',Georgia,serif!important;color:#173a31!important}
.cta-band:after{border-color:#c59b62!important;box-shadow:none!important}
.page-hero{padding:clamp(58px,8vw,100px) 0;background:#ecece3!important}
.page-hero-grid{grid-template-columns:minmax(0,1fr) minmax(300px,.78fr);gap:clamp(36px,7vw,100px)}
.page-hero h1{font-size:clamp(58px,8vw,104px)!important;line-height:.9!important;margin:18px 0!important;max-width:760px}
.page-hero p{font-size:15px!important;color:#5c6b61!important;max-width:540px}
.page-hero img{height:clamp(280px,34vw,430px)!important;object-fit:cover!important;border-radius:0!important;border:0!important;transform:none!important}
.detail-grid{gap:clamp(35px,7vw,100px)}
.detail-grid h2{font-size:clamp(42px,5.5vw,72px)!important;line-height:.95!important}
.check-list{gap:0 20px}
.check-item{padding:18px 4px!important;border:0!important;border-bottom:1px solid #d4d4ca!important;border-radius:0!important;background:transparent!important;font-size:12px!important;color:#45574c}
.check-item:before{background:#173a31!important;color:#f5f3ed!important;border-radius:0!important;font-size:11px}
.form-layout{gap:clamp(30px,6vw,84px)}
.contact-list{border-top:1px solid #d4d4ca;padding-top:18px}
.contact-icon{border-radius:0!important;background:#e7e8de!important;color:#173a31}
.quote-form,.upload-card,.qr-card{background:#fffefb!important;border:1px solid #d4d4ca!important;border-radius:0!important;padding:clamp(22px,4vw,44px)!important}
.quote-form h2,.upload-card h1,.qr-card h1{font-size:clamp(39px,5vw,62px)!important;line-height:.98!important}
.field{font-size:10px;text-transform:uppercase;letter-spacing:.045em;color:#405348}
.field input,.field select,.field textarea{border:0!important;border-bottom:1px solid #b9c1b5!important;border-radius:0!important;background:#f5f3ed!important;padding:13px!important;color:#173a31!important}
.field input:focus,.field select:focus,.field textarea:focus{border-color:#173a31!important;outline:2px solid #c59b62!important;outline-offset:2px;box-shadow:none!important}
.form-status,.upload-result{background:#e7e8de!important;border-radius:0!important;color:#173a31!important}
.upload-shell,.qr-shell{padding:clamp(45px,7vw,90px) 0!important;background:#f5f3ed!important}
.upload-grid{gap:20px}
.upload-card>p,.qr-card>p{color:#68716a!important}
.upload-note{color:#68716a!important}
.qr-image{border:1px solid #c9cbc0!important;border-radius:0!important;padding:15px!important;box-shadow:none!important}
.qr-actions{gap:9px}
.catalogue-callout{background:transparent!important;border:1px solid #c9cbc0!important;border-radius:0!important;padding:22px!important}
.footer{background:#173a31!important;border-top:0!important;padding:60px 0 24px}
.footer-grid{border-color:#ffffff38;grid-template-columns:1.2fr .8fr .9fr 1fr}
.footer h3{font-size:9px;letter-spacing:.2em;color:#d7c69f!important}
.footer a:hover{color:#e4c18f!important}
.footer .brand-mark{background:#f5f3ed!important;color:#173a31!important}
.whatsapp{background:#173a31!important;border:1px solid #c59b62!important;border-radius:2px!important;padding:12px 16px!important;font-size:9px!important;letter-spacing:.1em;text-transform:uppercase}
.photo-credit{padding:0 2px}
@media(max-width:900px){.wrap{width:min(100% - 40px,760px)}.hero:after{top:10%;right:-8vw}.hero-grid,.page-hero-grid{grid-template-columns:1fr}.hero-grid{gap:42px}.hero-visual{max-width:720px}.hero-visual img{height:clamp(340px,65vw,480px)}.page-hero-grid>img{max-width:640px}.section-head{align-items:start;flex-direction:column}.service-panel.premium-services{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:600px){.wrap{width:calc(100% - 32px)}.topline .wrap{font-size:9px}.hero{padding:72px 0 58px}.hero:before{width:calc(100% - 32px);font-size:8px}.hero:after{font-size:100px;top:15%;right:-3vw}.hero h1{font-size:clamp(64px,18vw,100px)!important}.hero-visual{padding:0 9px 9px 0}.hero-visual:before{inset:10px -1px -1px 10px}.hero-visual img{height:clamp(260px,76vw,360px)}.floating-note{left:-5px;top:12px}.visual-caption{left:10px;right:18px;bottom:10px;padding:13px}.strip-item{padding:16px 10px!important}.strip-item span{font-size:8px}.section{padding:58px 0}.cards,.service-panel,.service-panel.premium-services,.check-list,.form-grid{grid-template-columns:1fr!important}.card img{height:240px!important}.service-feature,.service-panel.premium-services .service-feature{min-height:300px!important}.page-hero{padding:48px 0}.page-hero h1{font-size:clamp(54px,15vw,78px)!important}.page-hero img{height:250px!important}.quote-form,.upload-card,.qr-card{padding:22px!important}.footer-grid{grid-template-columns:1fr;gap:26px}.catalogue-callout{align-items:flex-start;flex-direction:column}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important}}

/* Homepage campaign hero: the photograph is the atmosphere, not a side card. */
.hero{min-height:min(820px,88svh);padding:34px 0 0!important;overflow:hidden;background:#173a31!important;color:#fffefb}
.hero:before{z-index:4;top:20px;color:#ffffffbf!important;border-color:#ffffff42!important}
.hero:after{display:none!important}
.hero-grid{display:block!important;position:relative;min-height:min(820px,88svh);width:100%!important;max-width:none!important;margin:0!important;padding:0!important}
.hero-grid>div:first-child{position:relative;z-index:3;width:min(1320px,calc(100% - 64px));min-height:min(820px,88svh);margin:0 auto;padding:clamp(130px,17vh,210px) 0 180px;pointer-events:none}
.hero-grid>div:first-child>*{pointer-events:auto}
.hero-grid>div:first-child .eyebrow{color:#e4d7bc!important}
.hero-grid>div:first-child .eyebrow:before{background:#c59b62!important}
.hero .hero-grid h1{max-width:850px;margin:26px 0 22px!important;color:#fffefb!important;font-size:clamp(78px,10vw,142px)!important;line-height:.82!important;letter-spacing:-.045em!important}
.hero .hero-grid h1 span{color:#e1bd83!important}
.hero .lead{max-width:470px;color:#f1f0e9!important;font-size:clamp(14px,1.35vw,18px);line-height:1.8}
.hero .actions{margin-top:32px}
.hero .btn-primary{background:#f5f3ed!important;border-color:#f5f3ed!important;color:#173a31!important}
.hero .btn-primary:hover{background:#e1bd83!important;border-color:#e1bd83!important}
.hero .btn-light{background:transparent!important;border-color:#ffffffa6!important;color:#fffefb!important}
.hero .mockup-label{padding:0!important;border:0!important;border-radius:0!important;background:transparent!important;color:#eee9dc!important;font-size:9px;letter-spacing:.17em}
.hero .hero-visual{position:absolute!important;inset:0!important;z-index:1;width:100%!important;max-width:none!important;margin:0!important;padding:0!important;overflow:hidden;background:#173a31}
.hero .hero-visual:before{display:none!important}
.hero .hero-visual:after{content:'';position:absolute;inset:0;z-index:1;pointer-events:none;background:linear-gradient(90deg,rgba(13,35,29,.88) 0%,rgba(13,35,29,.68) 36%,rgba(13,35,29,.2) 72%,rgba(13,35,29,.08) 100%),linear-gradient(0deg,rgba(13,35,29,.4),transparent 42%)}
.hero .hero-visual img,.hero .hero-carousel img{position:absolute;inset:0;width:100%!important;height:100%!important;object-fit:cover!important;object-position:center 48%;border:0!important;border-radius:0!important;opacity:1;transform:none!important;transition:opacity .8s ease!important}
.hero .hero-carousel img.is-changing{opacity:.16!important}
.hero .hero-slide-link{position:absolute;inset:0;z-index:0;display:block}
.hero .hero-slide-link:after{display:none!important}
.hero .hero-carousel .floating-note{z-index:2;top:92px;right:max(32px,calc((100vw - 1320px)/2));left:auto;border:1px solid #ffffff66!important;border-radius:0!important;background:#173a318c!important;color:#fffefb!important;padding:12px 15px;font-size:9px;letter-spacing:.17em;backdrop-filter:blur(8px)}
.hero .hero-carousel .visual-caption{z-index:2;left:auto;right:max(32px,calc((100vw - 1320px)/2));bottom:34px;max-width:400px;background:transparent!important;border:0!important;color:#fffefb;padding:0;text-align:right}
.hero .hero-caption-copy small{color:#e1bd83!important;font-size:9px;letter-spacing:.2em}
.hero .hero-caption-copy strong{font:400 clamp(22px,3vw,38px)/1.02 'Instrument Serif',Georgia,serif!important;color:#fffefb}
.hero .hero-slide-more{color:#fffefb;font-size:9px;text-transform:uppercase;letter-spacing:.14em}
.hero .hero-carousel-controls{z-index:3;top:auto;right:auto;bottom:35px;left:max(32px,calc((100vw - 1320px)/2));gap:8px;padding:0;border:0;border-radius:0;background:transparent;backdrop-filter:none}
.hero .hero-carousel-controls button{width:42px;height:42px;border:1px solid #ffffff8a;border-radius:50%;background:transparent;color:#fffefb;font-size:14px}
.hero .hero-carousel-controls button:hover{background:#ffffff22}
.hero .hero-carousel-controls [data-hero-dots]{gap:7px}
.hero .hero-carousel-controls [data-hero-dots] button{width:7px;height:7px;min-width:7px;border:0;background:#ffffff80}
.hero .hero-carousel-controls [data-hero-dots] button[aria-current=true]{width:24px;border-radius:8px;background:#e1bd83}
.hero .strip-item,.hero .card{pointer-events:auto}
@media(max-width:900px){.hero,.hero-grid,.hero-grid>div:first-child{min-height:780px}.hero-grid>div:first-child{width:calc(100% - 40px);padding:150px 0 190px}.hero .hero-visual img{height:100%!important}.hero .hero-carousel .floating-note{right:20px;top:94px}.hero .hero-carousel .visual-caption{right:20px;bottom:28px}.hero .hero-carousel-controls{left:20px;bottom:30px}.hero .hero-grid h1{font-size:clamp(70px,12vw,110px)!important}}
@media(max-width:600px){.hero,.hero-grid,.hero-grid>div:first-child{min-height:790px}.hero-grid>div:first-child{width:calc(100% - 32px);padding:138px 0 190px}.hero .hero-grid h1{font-size:clamp(64px,17vw,92px)!important}.hero .lead{max-width:340px;font-size:14px}.hero .hero-carousel .floating-note{top:90px;right:16px;padding:9px 11px;font-size:8px}.hero .hero-carousel .visual-caption{right:16px;bottom:28px;max-width:230px}.hero .hero-caption-copy strong{font-size:25px}.hero .hero-carousel-controls{left:16px;bottom:30px}.hero .hero-carousel-controls button{width:36px;height:36px}.hero .hero-visual:after{background:linear-gradient(90deg,rgba(13,35,29,.84),rgba(13,35,29,.36)),linear-gradient(0deg,rgba(13,35,29,.6),transparent 55%)}}
@media(prefers-reduced-motion:reduce){.hero .hero-carousel img{transition:none!important}}

/* Softer, tactile surfaces across every page—rounded and quiet, never shadow-heavy. */
:root{--soft-line:#e0e4dc;--soft-line-strong:#d3dbd1}
.card{background:#fffefb!important;border:1px solid var(--soft-line)!important;border-radius:16px!important;box-shadow:none!important}
.card img{border-radius:15px 15px 0 0!important}
.card-body{padding:22px!important}
.card:hover{border-color:var(--soft-line-strong)!important}
.service-feature,.service-panel.premium-services .service-feature{border-radius:18px!important;overflow:hidden;box-shadow:none!important}
.cta-band{border-radius:18px!important;border-color:var(--soft-line-strong)!important;box-shadow:none!important}
.cta-band:after{border-radius:14px!important}
.page-hero-grid>img{border-radius:16px!important}
.quote-form,.upload-card,.qr-card{border-radius:18px!important;border-color:var(--soft-line)!important;box-shadow:none!important}
.field input,.field select,.field textarea{border:1px solid #d9dfd6!important;border-radius:9px!important;background:#fbfbf7!important}
.form-status,.upload-result{border-radius:10px!important}
.check-item{border:1px solid var(--soft-line)!important;border-radius:10px!important;background:#fbfbf7!important}
.check-item:before{border-radius:7px!important}
.contact-icon{border:1px solid var(--soft-line)!important;border-radius:10px!important}
.catalogue-callout{border:1px solid var(--soft-line)!important;border-radius:14px!important;background:#fbfbf7!important}
.qr-image{border-color:var(--soft-line-strong)!important;border-radius:14px!important}
.btn,.header .btn,.whatsapp{border-radius:999px!important;box-shadow:none!important}
.hero .hero-carousel .floating-note{border-radius:999px!important}
.hero .hero-carousel-controls button{border-radius:50%!important}
.strip{border-color:var(--soft-line)!important}
.strip-item{border-color:var(--soft-line)!important}
.section-head{border-color:var(--soft-line-strong)!important}
.section.dark .section-head{border-color:#ffffff2e!important}
.contact-list{border-color:var(--soft-line-strong)!important}
.qr-actions button{border-radius:999px!important}
@media(max-width:600px){.card-body{padding:19px!important}}
/* Rounded finish v2: force a visibly softer silhouette. */
.card{border-radius:20px!important}
.card img{border-radius:19px 19px 0 0!important}
.service-feature,.service-panel.premium-services .service-feature{border-radius:22px!important}
.cta-band,.quote-form,.upload-card,.qr-card{border-radius:22px!important}
.page-hero-grid>img{border-radius:18px!important}
.check-item,.catalogue-callout{border-radius:14px!important}
.contact-icon{border-radius:12px!important}
.field input,.field select,.field textarea{border-radius:11px!important}
.mobile-nav{border-radius:14px!important}

'''

JS = r'''(()=>{
const menu=document.querySelector('[data-menu-button]');
const nav=document.querySelector('[data-mobile-nav]');
if(menu&&nav){
  const setMenuOpen=open=>{
    nav.classList.toggle('open',open);
    menu.setAttribute('aria-expanded',String(open));
    menu.setAttribute('aria-label',open?'Close navigation':'Open navigation');
    menu.textContent=open?'×':'☰';
  };
  menu.addEventListener('click',()=>setMenuOpen(!nav.classList.contains('open')));
  nav.addEventListener('click',event=>{
    if(event.target.closest('a'))setMenuOpen(false);
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&nav.classList.contains('open')){
      setMenuOpen(false);
      menu.focus();
    }
  });
}
const main=document.querySelector('main[data-content-page]');
const pageKey=main?.dataset.contentPage;
const localApiBase=['localhost','127.0.0.1'].includes(location.hostname)&&['4173','4174','5173'].includes(location.port)?'http://127.0.0.1:8000':'';
const apiBase=(window.ESICOM_API_BASE_URL||localApiBase).replace(/\/$/,'');
const imageUrl=path=>{
  if(/^(?:https?:|blob:|data:)/i.test(path))return path;
  const base=apiBase&&path.startsWith('/media/')?apiBase:location.origin;
  return new URL(path,base).href;
};
let photoOverrides={};
const siteImage=path=>{
  if(/^https?:\/\//i.test(path))return path;
  return imageUrl(photoOverrides[path]||path);
};
const visualEditorMode=new URLSearchParams(location.search).get('editor')==='1'&&window.parent!==window;
const editorParentOrigin=visualEditorMode?new URLSearchParams(location.search).get('editor_origin'):'';
const visualOriginals=new Map();
const editorSelector=element=>{
  const root=element.closest('main[data-content-page],header,footer,.topline');
  if(!root)return '';
  const rootSelector=root.matches('main[data-content-page]')
    ?'main[data-content-page="'+pageKey+'"]'
    :root.matches('.topline')?'.topline':root.localName;
  const marker=element.closest('[data-editor-key]');
  const stableMarker=marker&&root.contains(marker)?marker:null;
  const parts=[];
  let current=element;
  const stopAt=stableMarker||root;
  while(current&&current!==stopAt){
    const siblings=[...current.parentElement.children].filter(sibling=>sibling.tagName===current.tagName);
    parts.unshift(current.localName+':nth-of-type('+(siblings.indexOf(current)+1)+')');
    current=current.parentElement;
  }
  if(stableMarker){
    const markerSelector='[data-editor-key="'+stableMarker.dataset.editorKey+'"]';
    return rootSelector+' '+markerSelector+(parts.length?' > '+parts.join(' > '):'');
  }
  return current===root?rootSelector+' > '+parts.join(' > '):'';
};
const directText=element=>[...element.childNodes]
  .filter(node=>node.nodeType===Node.TEXT_NODE)
  .map(node=>node.textContent)
  .join('')
  .trim();
const rememberOriginal=target=>{
  const selector=editorSelector(target);
  if(selector&&!visualOriginals.has(selector)){
    visualOriginals.set(selector,{
      textNodes:[...target.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent),
      image:target instanceof HTMLImageElement?target.getAttribute('src'):'',
      fontFamily:target.style.fontFamily,
      fontSize:target.style.fontSize,
      color:target.style.color,
      display:target.style.display,
    });
  }
  return visualOriginals.get(selector);
};
const setDirectText=(target,value)=>{
  const textNodes=[...target.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE);
  if(textNodes.length){
    textNodes[0].textContent=value;
    textNodes.slice(1).forEach(node=>node.remove());
  }else target.insertBefore(document.createTextNode(value),target.firstChild);
};
const applyVisualEdits=edits=>{
  for(const edit of edits){
    if(edit.page!==pageKey&&edit.page!=='global')continue;
    const target=document.querySelector(edit.selector);
    if(!target)continue;
    rememberOriginal(target);
    if(edit.text!==null)setDirectText(target,edit.text);
    if(edit.image&&target instanceof HTMLImageElement)target.src=imageUrl(edit.image);
    if(edit.font_family)target.style.fontFamily='"'+edit.font_family+'"';
    if(edit.font_size)target.style.fontSize=edit.font_size+'px';
    if(edit.text_color)target.style.color=edit.text_color;
    if(edit.hidden)target.style.display='none';
  }
};
if(visualEditorMode){
  document.body.classList.add('visual-editor-mode');
  window.addEventListener('message',event=>{
    if(event.origin!==editorParentOrigin||event.source!==parent||event.data?.type!=='esicom-visual-editor-preview')return;
    const edit=event.data.edit;
    const target=document.querySelector(edit.selector);
    if(!target)return;
    const original=rememberOriginal(target);
    if(edit.text===null){
      const textNodes=[...target.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE);
      textNodes.forEach(node=>node.remove());
      original.textNodes.forEach(text=>target.insertBefore(document.createTextNode(text),target.firstChild));
    }else setDirectText(target,edit.text);
    if(target instanceof HTMLImageElement){
      if(edit.image!==null)target.src=edit.image?imageUrl(edit.image):imageUrl(original.image);
    }
    target.style.fontFamily=edit.font_family?'"'+edit.font_family+'"':original.fontFamily;
    target.style.fontSize=edit.font_size?edit.font_size+'px':original.fontSize;
    target.style.color=edit.text_color||original.color;
    target.style.display=edit.hidden?'none':original.display;
  });
  document.addEventListener('click',event=>{
    const target=event.target.closest('img,h1,h2,h3,p,a,button,span,small,strong,b,li,.eyebrow,.mockup-label');
    if(!target||!target.closest('main[data-content-page],header,footer,.topline'))return;
    event.preventDefault();
    event.stopImmediatePropagation();
    document.querySelector('.visual-editor-selected')?.classList.remove('visual-editor-selected');
    target.classList.add('visual-editor-selected');
    if(!editorParentOrigin)return;
    parent.postMessage({
      type:'esicom-visual-editor-select',
      page:pageKey,
      selector:editorSelector(target),
      tag:target.tagName.toLowerCase(),
      text:directText(target),
      image:target instanceof HTMLImageElement?target.src:'',
      alt:target instanceof HTMLImageElement?target.alt:'',
    },editorParentOrigin);
  },true);
}
const heroCarousel=pageKey==='home'?document.querySelector('.hero-visual'):null;
if(heroCarousel){
  heroCarousel.classList.add('hero-carousel');
  heroCarousel.setAttribute('role','region');
  heroCarousel.setAttribute('aria-roledescription','carousel');
  heroCarousel.setAttribute('aria-label','Featured Esicom supplies, printing and branding');
  const initialImage=heroCarousel.querySelector('[data-copy-image]');
  initialImage.removeAttribute('data-copy-image');
  initialImage.setAttribute('data-hero-slide-image','');
  initialImage.src='/images/hero/hero-office-supplies.webp';
  initialImage.alt='Esicom Suppliers branded notebooks and business cards on a forest-green desk';
  const note=document.createElement('div');
  note.className='floating-note';
  note.textContent='SUPPLY · PRINT · BRAND';
  const slideLink=document.createElement('a');
  slideLink.className='hero-slide-link';
  slideLink.setAttribute('data-hero-slide-link','');
  slideLink.href='/office-supplies/';
  slideLink.append(initialImage);
  const caption=document.createElement('div');
  caption.className='visual-caption';
  const captionCopy=document.createElement('div');
  captionCopy.className='hero-caption-copy';
  const captionCategory=document.createElement('small');
  captionCategory.setAttribute('data-hero-slide-category','');
  const captionTitle=document.createElement('strong');
  captionTitle.setAttribute('data-hero-slide-title','');
  captionCopy.append(captionCategory,captionTitle);
  const slideMore=document.createElement('a');
  slideMore.className='hero-slide-more';
  slideMore.setAttribute('data-hero-slide-more','');
  slideMore.href='/office-supplies/';
  slideMore.textContent='Explore ↗';
  caption.append(captionCopy,slideMore);
  const controls=document.createElement('div');
  controls.className='hero-carousel-controls';
  controls.setAttribute('aria-label','Photo slideshow controls');
  const previous=document.createElement('button');
  previous.type='button';
  previous.setAttribute('data-hero-previous','');
  previous.setAttribute('aria-label','Previous photo');
  previous.textContent='←';
  const dots=document.createElement('div');
  dots.setAttribute('data-hero-dots','');
  dots.setAttribute('aria-label','Choose a photo');
  const next=document.createElement('button');
  next.type='button';
  next.setAttribute('data-hero-next','');
  next.setAttribute('aria-label','Next photo');
  next.textContent='→';
  const toggle=document.createElement('button');
  toggle.type='button';
  toggle.setAttribute('data-hero-toggle','');
  controls.append(previous,dots,next,toggle);
  heroCarousel.replaceChildren(note,slideLink,caption,controls);
}
const imageSlides=[
  {image:'/images/hero/hero-office-supplies.webp',alt:'Esicom Suppliers branded notebooks and business cards on a forest-green desk',category:'Supply · Office essentials',title:'Give the everyday a signature.',href:'/office-supplies/'},
  {image:'/images/hero/hero-computer.webp',alt:'Computer and printer essentials in a contemporary office',category:'Supply · Computer essentials',title:'The essentials behind a productive team.',href:'/computer-consumables/'},
  {image:'/images/hero/hero-printing.webp',alt:'Fresh printed materials prepared in a professional print studio',category:'Print · Business printing',title:'Make your next print run stand out.',href:'/bulk-printing/'},
  {image:'/images/hero/hero-branding.webp?v=2',alt:'Forest-green Esicom Suppliers polo beside a plain ivory polo',category:'Brand · Corporate apparel',title:'Wear your identity with pride.',href:'/branding/'}
];
let carouselSlides=imageSlides;
let carouselActive=0;
let carouselTimer=null;
let carouselTransition=null;
let carouselPaused=visualEditorMode||window.matchMedia('(prefers-reduced-motion: reduce)').matches;
let homePageImage='';
let visualEditsCache=[];
const showHeroSlide=index=>{
  if(!heroCarousel||!carouselSlides.length)return;
  const image=heroCarousel.querySelector('[data-hero-slide-image]');
  const slideLink=heroCarousel.querySelector('[data-hero-slide-link]');
  const slideMore=heroCarousel.querySelector('[data-hero-slide-more]');
  const category=heroCarousel.querySelector('[data-hero-slide-category]');
  const title=heroCarousel.querySelector('[data-hero-slide-title]');
  const dots=heroCarousel.querySelector('[data-hero-dots]');
  carouselActive=(index+carouselSlides.length)%carouselSlides.length;
  const slide=carouselSlides[carouselActive];
  image.classList.add('is-changing');
  window.clearTimeout(carouselTransition);
  const renderSlide=()=>{
    image.src=siteImage(slide.image);
    image.alt=slide.alt;
    slideLink.href=slide.href;
    slideMore.href=slide.href;
    category.textContent=slide.category;
    title.textContent=slide.title;
    image.classList.remove('is-changing');
    if(heroCarousel){heroCarousel.querySelectorAll('[style]').forEach(el=>{el.style.fontFamily='';el.style.fontSize='';el.style.color='';el.style.display='';});}
    if(carouselActive===0&&heroCarousel){applyVisualEdits(visualEditsCache.filter(e=>{const t=document.querySelector(e.selector);return t&&heroCarousel.contains(t);}));}
  };
  if(visualEditorMode)renderSlide();
  else carouselTransition=window.setTimeout(renderSlide,150);
  for(const [dotIndex,button] of [...dots.children].entries()){
    button.setAttribute('aria-current',String(dotIndex===carouselActive));
    button.setAttribute('aria-label','Show photo '+(dotIndex+1)+' of '+carouselSlides.length);
  }
};
const setHeroPaused=nextPaused=>{
  if(!heroCarousel)return;
  const pauseButton=heroCarousel.querySelector('[data-hero-toggle]');
  carouselPaused=nextPaused;
  pauseButton.setAttribute('aria-pressed',String(carouselPaused));
  pauseButton.setAttribute('aria-label',carouselPaused?'Play photo slideshow':'Pause photo slideshow');
  pauseButton.textContent=carouselPaused?'▶':'Ⅱ';
  window.clearInterval(carouselTimer);
  if(!carouselPaused&&carouselSlides.length>1)carouselTimer=window.setInterval(()=>showHeroSlide(carouselActive+1),5500);
};
const startHeroCarousel=featuredProducts=>{
  if(!heroCarousel)return;
  const dots=heroCarousel.querySelector('[data-hero-dots]');
  const productSlides=featuredProducts.map(product=>({
    image:imageUrl(product.image),
    alt:product.name,
    category:'Featured · '+(product.page==='office-supplies'?'Office essentials':product.page.replaceAll('-',' ')),
    title:product.name,
    href:'/'+encodeURIComponent(product.page)+'/'
  }));
  carouselSlides=homePageImage
    ?[{image:imageUrl(homePageImage),alt:'Featured Esicom Suppliers photo',category:'ESICOM · SUPPLY. PRINT. BRAND.',title:'The details that keep your workday moving.',href:'/office-supplies/'},...imageSlides,...productSlides]
    :[...imageSlides,...productSlides];
  dots.replaceChildren(...carouselSlides.map((slide,index)=>{
    const button=document.createElement('button');
    button.type='button';
    button.setAttribute('aria-label','Show photo '+(index+1)+' of '+carouselSlides.length);
    button.setAttribute('aria-current',String(index===0));
    button.addEventListener('click',()=>showHeroSlide(index));
    return button;
  }));
  showHeroSlide(0);
  setHeroPaused(carouselPaused);
};
if(heroCarousel){
  heroCarousel.querySelector('[data-hero-previous]').addEventListener('click',()=>showHeroSlide(carouselActive-1));
  heroCarousel.querySelector('[data-hero-next]').addEventListener('click',()=>showHeroSlide(carouselActive+1));
  heroCarousel.querySelector('[data-hero-toggle]').addEventListener('click',()=>setHeroPaused(!carouselPaused));
  heroCarousel.addEventListener('mouseenter',()=>window.clearInterval(carouselTimer));
  heroCarousel.addEventListener('mouseleave',()=>{if(!carouselPaused&&carouselSlides.length>1)carouselTimer=window.setInterval(()=>showHeroSlide(carouselActive+1),5500)});
}
startHeroCarousel([]);
const productCard=product=>{
  const article=document.createElement('article');
  article.className='card';
  article.dataset.editorKey='product-'+product.slug;
  const link=document.createElement('a');
  link.href='/'+encodeURIComponent(product.page)+'/';
  const image=document.createElement('img');
  image.src=imageUrl(product.image);
  image.alt=product.name;
  image.loading='lazy';
  image.decoding='async';
  const body=document.createElement('div');
  body.className='card-body';
  const heading=document.createElement('h3');
  heading.textContent=product.name;
  const description=document.createElement('p');
  description.textContent=product.description;
  const more=document.createElement('span');
  more.className='link';
  more.textContent='Ask us about this';
  body.append(heading,description,more);
  link.append(image,body);
  article.append(link);
  return article;
};
const editableSection=section=>{
  const wrapper=document.createElement('section');
  wrapper.className='section editable-section';
  wrapper.dataset.editorKey='section-'+section.id;
  const content=document.createElement('div');
  content.className='wrap editable-section-card';
  if(section.image){
    const image=document.createElement('img');
    image.src=imageUrl(section.image);
    image.alt=section.title;
    image.loading='lazy';
    image.decoding='async';
    content.append(image);
  }
  const copy=document.createElement('div');
  copy.className='editable-section-copy';
  const heading=document.createElement('h2');
  heading.textContent=section.title;
  copy.append(heading);
  if(section.body){
    const body=document.createElement('p');
    body.textContent=section.body;
    copy.append(body);
  }
  if(section.button_text&&section.button_url){
    const button=document.createElement('a');
    button.className='btn btn-primary';
    button.href=section.button_url;
    button.textContent=section.button_text;
    copy.append(button);
  }
  content.append(copy);
  wrapper.append(content);
  return wrapper;
};
const loadSiteContent=async()=>{
  if(!main)return;
  const response=await fetch(apiBase+'/api/site-content/',{headers:{'Accept':'application/json'},cache:'no-store'});
  if(!response.ok)throw new Error('Site content service returned HTTP '+response.status);
  const content=await response.json();
  photoOverrides=content.photos||{};
  visualEditsCache=content.visual_edits||[];
  document.querySelectorAll('img[src]').forEach(image=>{
    const source=image.getAttribute('src');
    if(source&&photoOverrides[source])image.src=imageUrl(photoOverrides[source]);
  });
  const page=content.pages?.[pageKey];
  if(page){
    const eyebrow=main.querySelector('[data-copy-eyebrow]');
    if(eyebrow)eyebrow.textContent=page.eyebrow;
    const intro=main.querySelector('[data-copy-intro]');
    if(intro)intro.textContent=page.intro;
    const heading=main.querySelector('[data-copy-heading]');
    if(heading){
      const highlight=heading.querySelector('[data-copy-highlight]');
      if(highlight){
        const leadingText=[...heading.childNodes].find(node=>node.nodeType===Node.TEXT_NODE);
        if(leadingText)leadingText.textContent=page.title;
        highlight.textContent=page.highlight||'';
        highlight.hidden=!page.highlight;
      }else heading.textContent=page.title;
    }
    if(page.image){
      if(pageKey==='home')homePageImage=page.image;
      else{
        const heroImage=main.querySelector('[data-copy-image]');
        if(heroImage)heroImage.src=imageUrl(page.image);
      }
    }
  }
  const products=Array.isArray(content.products)?content.products:[];
  if(pageKey==='home'){
    const featured=products.filter(product=>product.featured);
    const container=main.querySelector('[data-featured-products]');
    if(container)container.replaceChildren(...featured.map(productCard));
    startHeroCarousel(featured);
  }else{
    const categoryProducts=products.filter(product=>product.page===pageKey);
    const section=main.querySelector('[data-category-products]');
    const container=section?.querySelector('[data-product-list]');
    if(container&&categoryProducts.length){
      container.replaceChildren(...categoryProducts.map(productCard));
      section.hidden=false;
    }
  }
  const sections=(Array.isArray(content.sections)?content.sections:[])
    .filter(section=>section.page===pageKey)
    .map(editableSection);
  main.append(...sections);
  applyVisualEdits(content.visual_edits||[]);
};
loadSiteContent().catch(error=>{
  console.info('Site editor is not connected; showing the built-in page content.',error);
});
document.querySelectorAll('[data-quote-form]').forEach(form=>form.addEventListener('submit',async e=>{
  e.preventDefault();
  const btn=form.querySelector('button[type=submit]');
  const status=form.querySelector('[data-form-status]');
  const fd=new FormData(form);
  const data=Object.fromEntries(fd.entries());
  const base=(window.ESICOM_API_BASE_URL||'').replace(/\/$/,'');
  btn.disabled=true;
  btn.textContent='Submitting…';
  status.textContent='';
  try{
    const response=await fetch(base+'/api/quote/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:data.name,company:data.company||'',email:data.email||'',phone:data.phone,needs:(data.service||'Business supplies')+': '+data.details,quantity:data.quantity||'',date:data.date||'',source:'website'})});
    const result=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(result.detail||'The quote service is temporarily unavailable.');
    status.textContent='Thank you. Your enquiry has been recorded. Reference: ES-'+result.reference+'. We will follow up using the details provided.';
    form.reset();
  }catch(err){
    const subject=encodeURIComponent('Esicom quote request — '+(data.service||'Business supplies'));
    const body=encodeURIComponent('Hello Esicom Suppliers,\n\nName: '+data.name+'\nOrganisation: '+(data.company||'Not provided')+'\nPhone: '+data.phone+'\nEmail: '+(data.email||'Not provided')+'\nRequirement: '+(data.service||'Business supplies')+'\nDetails: '+data.details+'\nQuantity: '+(data.quantity||'Not specified')+'\nRequired date: '+(data.date||'Not specified'));
    status.textContent=err.message+' An email draft will open as a fallback. If it does not open, email esicomsuppliers@gmail.com.';
    window.location.href='mailto:esicomsuppliers@gmail.com?subject='+subject+'&body='+body;
  }finally{
    btn.disabled=false;
    btn.textContent='Send your enquiry ↗';
  }
}));
const uploadForm=document.querySelector('[data-file-upload-form]');
if(uploadForm){
  const fileInput=uploadForm.querySelector('[name=file]');
  const conversionField=uploadForm.querySelector('[data-conversion-field]');
  const conversionSelect=uploadForm.querySelector('[name=conversion]');
  const submitButton=uploadForm.querySelector('[type=submit]');
  const status=uploadForm.querySelector('[data-upload-status]');
  const resultPanel=document.querySelector('[data-upload-result]');
  const downloadLink=resultPanel.querySelector('[data-upload-download]');
  const shareButton=resultPanel.querySelector('[data-upload-share]');
  const whatsappLink=resultPanel.querySelector('[data-upload-whatsapp]');
  const deliveryInputs=uploadForm.querySelectorAll('[name=delivery]');
  const fileSizeNote=uploadForm.querySelector('[data-file-size-note]');
  const updateDeliveryUi=()=>{
    const isEmail=selectedDelivery()==='email';
    fileSizeNote.textContent=isEmail
      ?'Email attachments up to 15 MB · Choose WhatsApp to share larger files.'
      :'Files up to 50 MB · WhatsApp sharing requires confirmation in your messaging app.';
    submitButton.textContent=isEmail?'Email file to Esicom':'Prepare file for WhatsApp';
  };
  let completedSubmission=null;
  let completedShareFile=null;
  const selectedDelivery=()=>uploadForm.querySelector('[name=delivery]').value||'email';
  deliveryInputs.forEach(input=>input.addEventListener('change',updateDeliveryUi));
  updateDeliveryUi();
  fileInput.addEventListener('change',()=>{
    const file=fileInput.files[0];
    conversionSelect.replaceChildren(new Option('Send original file',''));
    conversionField.hidden=true;
    completedSubmission=null;
    completedShareFile=null;
    if(!file)return;
    const extension=file.name.split('.').pop().toLowerCase();
    const conversions=extension==='pdf'
      ?[['docx','Word document (.docx)']]
      :['jpg','jpeg','png','webp'].includes(extension)
        ?[['jpeg','JPEG (.jpg)'],['png','PNG (.png)'],['webp','WebP (.webp)']]
        :[];
    conversions.forEach(([value,label])=>conversionSelect.add(new Option(label,value)));
    conversionField.hidden=!conversions.length;
    resultPanel.hidden=true;
    status.textContent='';
  });
  uploadForm.addEventListener('submit',async event=>{
    event.preventDefault();
    const file=fileInput.files[0];
    if(!file)return;
    const delivery=selectedDelivery();
    const maxBytes=delivery==='email'?15*1024*1024:50*1024*1024;
    if(file.size>maxBytes){
      status.textContent=delivery==='email'
        ?'Email attachments must be 15 MB or smaller. Choose WhatsApp to share larger files.'
        :'Choose a file that is 50 MB or smaller.';
      return;
    }
    submitButton.disabled=true;
    submitButton.textContent=delivery==='email'?'Sending email attachment…':'Preparing WhatsApp file…';
    status.textContent='';
    resultPanel.hidden=true;
    try{
      const payload=new FormData(uploadForm);
      payload.set('delivery',delivery);
      const response=await fetch(apiBase+'/api/file-submissions/',{method:'POST',body:payload});
      const result=await response.json().catch(()=>({}));
      if(!response.ok){
        const error=new Error(result.detail||'The file upload service is unavailable.');
        error.saved=Boolean(result.saved);
        error.reference=result.reference;
        throw error;
      }
      const downloadUrl=new URL(result.download_url,apiBase?apiBase+'/':location.origin).href;
      completedSubmission={...result,downloadUrl};
      completedShareFile=result.converted?null:file;
      const supportsFileShare=sharedFile=>navigator.share&&navigator.canShare&&navigator.canShare({files:[sharedFile]});
      shareButton.hidden=delivery!=='whatsapp'||(!result.converted&&!supportsFileShare(file));
      shareButton.disabled=Boolean(result.converted);
      shareButton.textContent=result.converted?'Preparing share file…':'Share file…';
      whatsappLink.hidden=delivery!=='whatsapp';
      downloadLink.href=downloadUrl;
      downloadLink.textContent='Download '+result.filename;
      whatsappLink.href='https://wa.me/254728942669?text='+encodeURIComponent('Hello Esicom Suppliers, I submitted file reference ES-F'+result.reference+'.');
      resultPanel.querySelector('[data-upload-confirmation]').textContent=delivery==='email'
        ?'Your file was emailed to Esicom as an attachment. Reference: ES-F'+result.reference+'. A private backup copy stays available until staff deletes the submission.'
        :'Your file is ready to share. Choose Share file, select WhatsApp and Esicom, then confirm Send. Reference: ES-F'+result.reference+'.';
      resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=delivery!=='whatsapp';
      resultPanel.hidden=false;
      uploadForm.reset();
      conversionField.hidden=true;
      updateDeliveryUi();
      status.textContent='';
      if(result.converted&&navigator.share&&navigator.canShare){
        fetch(downloadUrl).then(response=>{
          if(!response.ok)throw new Error('The prepared file could not be downloaded.');
          return response.blob();
        }).then(blob=>{
          completedShareFile=new File([blob],result.filename,{type:blob.type||'application/octet-stream'});
          if(supportsFileShare(completedShareFile)){
            shareButton.hidden=false;
            shareButton.disabled=false;
            shareButton.textContent='Share file…';
          }else{
            shareButton.hidden=true;
            resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=false;
          }
        }).catch(error=>{
          shareButton.hidden=true;
          shareButton.disabled=true;
          status.textContent=error.message+' You can still download the file and attach it in WhatsApp.';
          resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=false;
        });
      }else if(result.converted){
        shareButton.hidden=true;
        resultPanel.querySelector('[data-upload-whatsapp-note]').hidden=false;
      }
    }catch(error){
      status.textContent=error.saved
        ?error.message
        :error.message+' Your file has not been confirmed as sent; please try again.';
    }finally{
      submitButton.disabled=false;
      updateDeliveryUi();
    }
  });
  shareButton.addEventListener('click',()=>{
    if(!completedSubmission||!completedShareFile)return;
    try{
      if(!navigator.share||!navigator.canShare||!navigator.canShare({files:[completedShareFile]})){
        status.textContent='Your file is ready. Download it, open WhatsApp, and attach the file to your message.';
        return;
      }
      navigator.share({files:[completedShareFile],title:'File for Esicom Suppliers',text:'File submission ES-F'+completedSubmission.reference}).catch(error=>{
        if(error.name!=='AbortError')status.textContent=error.message||'File sharing is unavailable in this browser. Download the file and attach it in WhatsApp.';
      });
    }catch(error){
      if(error.name!=='AbortError')status.textContent=error.message||'File sharing is unavailable in this browser. Download the file and attach it in WhatsApp.';
    }
  });
}
const qrImage=document.querySelector('[data-upload-qr]');
if(qrImage){
  const qrUrl=apiBase+'/api/file-upload-qr/';
  qrImage.src=qrUrl;
  const downloadQr=document.querySelector('[data-qr-download]');
  if(downloadQr)downloadQr.href=qrUrl;
}
document.querySelector('[data-print-qr]')?.addEventListener('click',()=>window.print());
})();'''

NAV = [('/office-supplies/','Office supplies'),('/computer-consumables/','Computer consumables'),('/bulk-printing/','Bulk printing'),('/branding/','Branding'),('/about/','About'),('/contact/','Contact'),('/send-file/','Send a file')]
SITE_ORIGIN = ''

def esc(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def header(path):
    links=''.join(f'<a href="{href}"'+(' aria-current="page"' if path==href else '')+f'>{label}</a>' for href,label in NAV)
    return f'''<a class="skip-link" href="#main-content">Skip to main content</a><div class="topline"><div class="wrap"><span>SUPPLY. PRINT. BRAND.</span><span>Chaka Place Building · Nairobi, Kenya &nbsp; | &nbsp; <a href="mailto:esicomsuppliers@gmail.com">esicomsuppliers@gmail.com</a></span></div></div><header class="header"><div class="wrap navrow"><a class="brand" href="/" aria-label="Esicom Suppliers home"><span class="brand-mark">E.</span><span><span class="brand-name">ESICOM</span><span class="brand-sub">Suppliers</span></span></a><nav class="navlinks" aria-label="Main navigation">{links}</nav><div class="nav-actions"><a class="btn btn-light catalogue-btn" href="/catalogue/esicom-suppliers-catalogue.pdf" download>Catalogue ↓</a><a class="btn btn-primary quote-btn" href="/contact/">Request a quote ↗</a><button class="menu-btn" data-menu-button aria-controls="mobile-navigation" aria-expanded="false" aria-label="Open navigation">☰</button></div></div><nav class="mobile-nav" id="mobile-navigation" data-mobile-nav aria-label="Mobile navigation">{links}<a href="/catalogue/esicom-suppliers-catalogue.pdf" download>Download product catalogue (PDF)</a><a href="/contact/">Request a quote ↗</a></nav></header>'''

def footer():
    return '''<footer class="footer"><div class="wrap"><div class="footer-grid"><div><a class="brand" href="/" style="color:white"><span class="brand-mark" style="background:#fff;color:#10243d">E.</span><span><span class="brand-name">ESICOM</span><span class="brand-sub" style="color:#b9c8d8">Suppliers</span></span></a><p style="max-width:290px;line-height:1.8">Office essentials, computer consumables, bulk printing and corporate branding.</p><p style="font:800 18px Manrope,sans-serif;color:white">SUPPLY. PRINT. BRAND.</p></div><div><h3>Products</h3><div class="footer-links"><a href="/office-supplies/">Office supplies</a><a href="/paper-filing/">Paper & filing</a><a href="/computer-consumables/">Computer consumables</a><a href="/catalogue/esicom-suppliers-catalogue.pdf" download>Product catalogue (PDF)</a></div></div><div><h3>Services</h3><div class="footer-links"><a href="/bulk-printing/">Bulk printing</a><a href="/branding/">Corporate branding</a><a href="/business-cards/">Business cards</a><a href="/branded-apparel/">Branded apparel</a><a href="/diaries-asset-tags/">Diaries & asset tags</a><a href="/send-file/">Send a file</a><a href="/file-qr/">Print the file QR</a></div></div><div><h3>Contact</h3><div class="footer-links"><a href="mailto:esicomsuppliers@gmail.com">esicomsuppliers@gmail.com</a><a href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20have%20an%20enquiry." target="_blank" rel="noopener noreferrer">WhatsApp · 0728 942 669</a><p>Chaka Place Building,<br>Arwings Kodhek Road,<br>Nairobi, Kenya</p><a href="https://www.google.com/maps/search/?api=1&query=Chaka+Place+Building%2C+Arwings+Kodhek+Road%2C+Nairobi%2C+Kenya" target="_blank" rel="noopener noreferrer">Open location in Maps ↗</a></div></div></div><div class="footer-bottom"><span>© <span data-year></span> Esicom Suppliers. All rights reserved.</span><span>Product availability and quotations confirmed on enquiry.</span></div></div></footer><a class="whatsapp" href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20would%20like%20to%20make%20an%20enquiry." target="_blank" rel="noopener noreferrer" aria-label="Chat with Esicom Suppliers on WhatsApp">◉ WhatsApp us</a><script>document.querySelector('[data-year]').textContent=new Date().getFullYear()</script><script src="/site.js?v=7" defer></script>'''

def catalogue_callout():
    return '<div class="catalogue-callout"><div><strong>Prefer a quick overview?</strong><p>Download the product and services catalogue as a PDF.</p></div><a class="btn btn-primary" href="/catalogue/esicom-suppliers-catalogue.pdf" download>Download catalogue ↓</a></div>'

def quote_form():
    return '''<form class="quote-form" data-quote-form><h2>Let’s start with your brief</h2><p>Tell us a little about what your team needs. We’ll follow up to talk through the details.</p><div class="form-grid"><label class="field">Full name *<input name="name" required minlength="2" maxlength="120" autocomplete="name" placeholder="Your full name"></label><label class="field">Organisation<input name="company" maxlength="160" autocomplete="organization" placeholder="Company or organisation"></label><label class="field">Phone number *<input name="phone" required maxlength="40" autocomplete="tel" placeholder="Your best contact number"></label><label class="field">Email address<input name="email" type="email" maxlength="254" autocomplete="email" placeholder="you@example.com"></label><label class="field full">What do you need? *<select name="service" required><option value="Office supplies">Office supplies</option><option value="Computer consumables">Computer consumables</option><option value="Bulk printing">Bulk printing</option><option value="Corporate branding">Corporate branding</option><option value="Business cards">Business cards</option><option value="Branded apparel">Branded apparel</option><option value="Diaries and asset tags">Diaries and asset tags</option><option value="Other requirement">Other requirement</option></select></label><label class="field">Estimated quantity<input name="quantity" maxlength="100" placeholder="If known"></label><label class="field">Required date<input name="date" type="date"></label><label class="field full">Tell us more *<textarea name="details" required minlength="8" maxlength="5000" placeholder="Add product names, quantities, specifications, artwork or timing."></textarea></label></div><button type="submit" class="btn btn-primary" style="width:100%;margin-top:20px">Send your enquiry ↗</button><a class="btn btn-light" style="width:100%;margin-top:10px" href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20would%20like%20a%20quote." target="_blank" rel="noopener noreferrer">Continue on WhatsApp ↗</a><div class="form-status" data-form-status role="status" aria-live="polite"></div><p style="margin-top:12px;font-size:11px">Prefer email? <a href="mailto:esicomsuppliers@gmail.com"><b>esicomsuppliers@gmail.com</b></a></p></form>'''

def card(href, image, title, desc, label='Explore details', credit=None):
    credit_html=f'<small class="photo-credit">{credit}</small>' if credit else ''
    return f'<article class="card"><a href="{href}"><img src="{image}" alt="{esc(title)}" loading="lazy"><div class="card-body"><h3>{esc(title)}</h3><p>{esc(desc)}</p><span class="link">{label}</span></div></a>{credit_html}</article>'

def home_content():
    products=card('/office-supplies/','/images/photography/stock-boxed-pens.webp','Packaged pen','A real packaged pen. Ask us about the pens and everyday stationery your team needs.',credit='<a href="https://commons.wikimedia.org/wiki/File:Colorex_in_Verpackung.jpg" target="_blank" rel="noopener noreferrer">Photo: Oliver Laumann · CC BY-SA 4.0</a>')+card('/computer-consumables/','/images/photography/computer.webp','Computer consumables','Toners, cartridges and computer essentials. Tell us your printer model.')+card('/paper-filing/','/images/photography/stock-copy-paper.webp','Copy paper by the ream','A real photo of copy-paper reams. Ask us about paper sizes and quantities.',credit='<a href="https://commons.wikimedia.org/wiki/File:6_reams_of_paper_stacked_on_the_floor.jpg" target="_blank" rel="noopener noreferrer">Photo: Sage Ross · CC BY-SA 3.0</a>')
    services='''<a class="service-feature" href="/bulk-printing/"><img src="/images/photography/printing.webp" alt="Printed pages prepared for a business print job" loading="lazy"><div><h3>Bulk printing</h3><p>Business documents and printed materials, planned around your brief.</p><span class="link" style="color:#fff">Explore printing</span></div></a><a class="service-feature" href="/branding/"><img src="/images/photography/apparel.webp" alt="Plain shirt ready for a branded apparel enquiry" loading="lazy"><div><h3>Corporate branding</h3><p>Business cards, apparel, diaries and the details that carry your identity.</p><span class="link" style="color:#fff">Explore branding</span></div></a><a class="service-feature" href="/about/"><img src="/images/photography/meeting-room.webp" alt="Bright modern meeting room" loading="lazy"><div><h3>One helpful point of contact</h3><p>Office supplies, printing and branding brought together in Nairobi.</p><span class="link" style="color:#fff">Get to know Esicom</span></div></a>'''
    branded=card('/business-cards/','/images/photography/printing.webp','Business cards','Printed details that help your team make a consistent first impression.')+card('/branded-apparel/','/images/photography/apparel.webp','Branded apparel','An easy way to bring your team’s identity together.')+card('/diaries-asset-tags/','/images/photography/stationery.webp','Diaries & asset tags','Practical branded stationery and identification enquiries.')
    return f'''<main><section class="hero"><div class="wrap hero-grid"><div><div class="eyebrow" data-copy-eyebrow>A Nairobi supplier for the workday</div><h1 data-copy-heading>Everything your office<br><span data-copy-highlight>needs.</span></h1><p class="lead" data-copy-intro>Everyday stationery, printing supplies and branded merchandise. Tell us what you need; we’ll take it from there.</p><div class="actions"><a class="btn btn-primary" href="/contact/">Tell us what you need ↗</a><a class="btn btn-light" href="/catalogue/esicom-suppliers-catalogue.pdf" download>Browse the catalogue ↓</a></div><div style="margin-top:25px"><span class="mockup-label">Chaka Place · Nairobi, Kenya</span></div></div><div class="hero-visual"><div class="floating-note">Your local business supplier</div><img data-copy-image src="/images/hero/hero-office-supplies.webp" alt="Esicom Suppliers branded notebooks and business cards on a forest-green desk" fetchpriority="high" decoding="async"><div class="visual-caption">Office essentials. Printing. Your brand.</div></div></div></section><section class="strip"><div class="wrap strip-grid"><div class="strip-item"><b>01</b><span>Office & workplace</span></div><div class="strip-item"><b>02</b><span>Computer essentials</span></div><div class="strip-item"><b>03</b><span>Business printing</span></div><div class="strip-item"><b>04</b><span>Corporate branding</span></div></div></section><section class="section"><div class="wrap"><div class="section-head"><div><div class="eyebrow">SUPPLY · THE EVERYDAY ESSENTIALS</div><h2>The things every office runs on.</h2></div><p>Boxes of pens, reams of paper and the essentials your team reaches for every day. Tell us what you need and we’ll put together a quote.</p></div><div class="cards" data-featured-products>{products}</div>{catalogue_callout()}</div></section><section class="section dark"><div class="wrap"><div class="section-head"><div><div class="eyebrow">PRINT · BRAND · Bring your brief</div><h2>Print, paper and branded merchandise.</h2></div><p>Send us your artwork, list or logo. We’ll help you work through the details.</p></div><div class="service-panel premium-services">{services}</div></div></section><section class="section white"><div class="wrap"><div class="section-head"><div><div class="eyebrow">BRAND · THE LITTLE THINGS</div><h2>Put your name on something useful.</h2></div><p>From shirts and diaries to everyday stationery, ask us about branded items for your team.</p></div><div class="cards">{branded}</div></div></section><section class="section"><div class="wrap"><div class="cta-band"><div><div class="eyebrow">A simpler next step</div><h2>Have a list or a logo?</h2><p style="margin:0;color:var(--muted)">Send it over. We’ll help you take it from there.</p></div><a class="btn btn-primary" href="/contact/">Start a conversation ↗</a></div></div></section></main>'''

def detail_content(path,data):
    items=data.get('items',[])
    if data['kind']=='branding':
        cards=card('/business-cards/','/images/photography/printing.webp','Business cards','Professional business card enquiries for meetings, introductions and networking.')+card('/branded-apparel/','/images/photography/apparel.webp','Branded shirts','Branded apparel enquiries for teams, events and everyday use.')+card('/diaries-asset-tags/','/images/photography/stationery.webp','Diaries & asset tags','Practical branded stationery and identification materials.')
        extra=f'<section class="section"><div class="wrap"><div class="section-head"><div><div class="eyebrow">Explore branding</div><h2>Choose a starting point.</h2></div><p>Photography is illustrative, not a portfolio of completed customer projects. Share your artwork and requirements for a tailored quotation.</p></div><div class="cards">{cards}</div></div></section>'
    else: extra=''
    lis=''.join(f'<div class="check-item">{esc(x)}</div>' for x in items)
    return f'''<main><section class="page-hero"><div class="wrap page-hero-grid"><div><div class="eyebrow" data-copy-eyebrow>{esc(data['eyebrow'])}</div><h1 data-copy-heading>{esc(data['title'])}</h1><p data-copy-intro>{esc(data['intro'])}</p><div class="actions"><a class="btn btn-primary" href="/contact/">Tell us what you need ↗</a><a class="btn btn-light" href="/catalogue/esicom-suppliers-catalogue.pdf" download>View the catalogue ↓</a></div></div><img data-copy-image src="{data['image']}" alt="Photograph illustrating {esc(data['eyebrow'].lower())}" loading="eager" decoding="async"></div></section><section class="section"><div class="wrap detail-grid"><div><div class="eyebrow">What do you need?</div><h2 style="font:800 clamp(29px,4vw,45px)/1.1 Manrope,sans-serif;letter-spacing:-.05em;margin:15px 0">Send us a list.<br><span style="color:var(--blue)">We’ll take it from there.</span></h2><p style="color:var(--muted);line-height:1.85">Add the sizes, quantities or product details you already know. We’ll follow up if we need anything else.</p><a class="btn btn-primary" href="/contact/">Ask us for a quote ↗</a></div><div class="check-list">{lis}</div></div></section><section class="section category-products" data-category-products data-category="{path.strip('/')}" hidden><div class="wrap"><div class="section-head"><div><div class="eyebrow">IN THE CATALOGUE</div><h2>Products we can help you source.</h2></div></div><div class="cards" data-product-list></div></div></section>{extra}<section class="section white"><div class="wrap"><div class="cta-band"><div><div class="eyebrow">A simpler next step</div><h2>Have a list or a logo?</h2><p style="margin:0;color:var(--muted)">Send it over. We’ll help you take it from there.</p></div><a class="btn btn-primary" href="/contact/">Start a conversation ↗</a></div></div></section></main>'''

def contact_content(data):
    return f'''<main><section class="page-hero"><div class="wrap page-hero-grid"><div><div class="eyebrow" data-copy-eyebrow>{data['eyebrow']}</div><h1 data-copy-heading>{data['title']}</h1><p data-copy-intro>{data['intro']}</p><span class="mockup-label">Chaka Place · Nairobi, Kenya</span></div><img data-copy-image src="{data['image']}" alt="A light-filled contemporary workspace" loading="eager" decoding="async"></div></section><section class="section"><div class="wrap form-layout"><div><div class="eyebrow">Contact Esicom</div><h2 style="font:800 clamp(30px,4vw,46px)/1.1 Manrope,sans-serif;letter-spacing:-.05em;margin:15px 0">A real conversation starts here.</h2><p style="color:var(--muted);line-height:1.8">Call, write or send a note about what your team needs. We’re based at Chaka Place in Nairobi.</p><div class="contact-list"><a class="contact-item" href="mailto:esicomsuppliers@gmail.com"><span class="contact-icon">✉</span><span><small>Email us</small><b>esicomsuppliers@gmail.com</b></span></a><a class="contact-item" href="https://wa.me/254728942669?text=Hello%20Esicom%20Suppliers%2C%20I%20would%20like%20to%20discuss%20a%20quotation." target="_blank" rel="noopener noreferrer"><span class="contact-icon">◉</span><span><small>WhatsApp enquiries</small><b>0728 942 669</b></span></a><div class="contact-item"><span class="contact-icon">⌖</span><span><small>Visit us</small><b>Chaka Place Building, Arwings Kodhek Road</b><small>Nairobi, Kenya</small></span></div><a class="link" href="https://www.google.com/maps/search/?api=1&query=Chaka+Place+Building%2C+Arwings+Kodhek+Road%2C+Nairobi%2C+Kenya" target="_blank" rel="noopener noreferrer">Open location in Maps ↗</a></div></div>{quote_form()}</div></section></main>'''

def upload_content():
    return '''<main><section class="upload-shell"><div class="wrap upload-grid"><form class="upload-card" data-file-upload-form><div class="eyebrow">SEND A FILE</div><h1>Share a file with Esicom.</h1><p>Choose a file, select email or WhatsApp, then send it to our team.</p><label class="field">File *<input type="file" name="file" accept=".pdf,.jpg,.jpeg,.png,.webp" required></label><p class="upload-note" data-file-size-note>Email attachments up to 15 MB · Choose WhatsApp to share larger files.</p><label class="field">Send using<select name="delivery"><option value="email">Email the file to Esicom</option><option value="whatsapp">Share the file with Esicom on WhatsApp</option></select></label><label class="field" data-conversion-field hidden>Convert to<select name="conversion"><option value="">Send original file</option></select></label><label class="field">Your name (optional)<input name="name" maxlength="120" autocomplete="name"></label><label class="field">Phone number (optional)<input name="phone" maxlength="40" autocomplete="tel"></label><label class="field">Message for Esicom (optional)<textarea name="note" maxlength="500" rows="3" placeholder="Add a short note about your file"></textarea></label><label class="field"><input type="checkbox" name="delivery_consent" required> I agree to send this file to Esicom using the delivery method selected above.</label><div aria-hidden="true" style="position:absolute;left:-10000px"><label>Leave this empty<input name="website" tabindex="-1" autocomplete="off"></label></div><button type="submit" class="btn btn-primary" style="width:100%;margin-top:20px">Email file to Esicom</button><p class="upload-note">PDF, JPG, PNG or WebP · Files stay private until Esicom staff deletes them.</p><div class="form-status" data-upload-status role="status" aria-live="polite"></div></form><aside class="upload-card"><div class="eyebrow">WHAT HAPPENS NEXT</div><h2>Email or WhatsApp.</h2><p>Email sends the actual file as an attachment to Esicom. WhatsApp opens your phone’s share screen; choose WhatsApp and the Esicom chat, then tap Send.</p><p class="upload-note">Email attachments are limited to 15 MB so email providers can accept them. WhatsApp sharing supports files up to 50 MB. PDF-to-Word conversion is best-effort and may change complex layouts; scanned PDFs need OCR for editable text.</p><a class="link" href="/file-qr/">Get the printable QR code ↗</a><div class="upload-result" data-upload-result hidden><p data-upload-confirmation role="status"></p><a class="btn btn-light" data-upload-download href="#">Download file</a><button type="button" class="btn btn-primary" data-upload-share hidden>Share file…</button><a class="btn btn-light" data-upload-whatsapp target="_blank" rel="noopener noreferrer">Open WhatsApp</a><p class="upload-note" data-upload-whatsapp-note hidden>If file sharing is unavailable in your browser, download the file and attach it to the Esicom WhatsApp chat.</p></div></aside></div></section></main>'''

def file_qr_content():
    return '''<main><section class="qr-shell"><div class="wrap"><div class="qr-card"><div class="eyebrow" style="justify-content:center">ESICOM SUPPLIERS · FILE UPLOAD</div><h1>Scan to send us a file.</h1><p class="qr-instructions">Scan this code with a phone camera to open our upload page. Customers can attach a PDF or photo, convert it if needed, and send it securely to our team.</p><img class="qr-image" data-upload-qr alt="QR code linking to the Esicom file upload page"><p class="upload-note">Files are private and stay available until Esicom staff deletes them. Uploads are limited to 50 MB. WhatsApp sharing requires the customer to confirm sending.</p><div class="qr-actions"><button class="btn btn-primary" type="button" data-print-qr>Print QR code</button><a class="btn btn-light" data-qr-download download="esicom-file-upload-qr.png">Download QR image</a><a class="btn btn-light" href="/send-file/">Open upload page</a></div></div></div></section></main>'''

def page_html(path,data):
    content=home_content() if data['kind']=='home' else contact_content(data) if data['kind']=='contact' else upload_content() if data['kind']=='upload' else file_qr_content() if data['kind']=='qr' else detail_content(path,data)
    title='Esicom Suppliers | '+('Supply. Print. Brand.' if path=='/' else data['eyebrow'].title())
    desc=esc(data['intro'])
    page_key='home' if path=='/' else path.strip('/')
    content=content.replace('<main>','<main id="main-content" tabindex="-1" data-content-page="'+page_key+'">',1)
    canonical=f'<link rel="canonical" href="{SITE_ORIGIN+path}">' if SITE_ORIGIN else ''
    social_url=f'<meta property="og:url" content="{SITE_ORIGIN+path}"><meta name="twitter:card" content="summary">' if SITE_ORIGIN else '<meta name="twitter:card" content="summary">'
    business_data=''
    if path=='/':
        business={"@context":"https://schema.org","@type":"LocalBusiness","name":"Esicom Suppliers","description":"Nairobi supplier of office supplies, computer consumables, printing and corporate branding.","email":"esicomsuppliers@gmail.com","telephone":"+254728942669","address":{"@type":"PostalAddress","streetAddress":"Chaka Place Building, Arwings Kodhek Road","addressLocality":"Nairobi","addressCountry":"KE"}}
        if SITE_ORIGIN:
            business['url']=SITE_ORIGIN
        business_data='<script type="application/ld+json">'+json.dumps(business,ensure_ascii=False,separators=(',',':'))+'</script>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="{NAVY}"><meta name="description" content="{desc}"><meta property="og:type" content="website"><meta property="og:site_name" content="Esicom Suppliers"><meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{desc}">{social_url}{canonical}<title>{esc(title)}</title><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/styles.css?v=5"><script src="/site-config.js?v=3"></script>{business_data}</head><body>{header(path)}{content}{footer()}</body></html>'''

def main():
    global SITE_ORIGIN
    SITE_ORIGIN=os.environ.get('ESICOM_PUBLIC_SITE_URL','').strip().rstrip('/')
    if SITE_ORIGIN:
        parsed_site_origin=urlsplit(SITE_ORIGIN)
        if parsed_site_origin.scheme!='https' or not parsed_site_origin.netloc or parsed_site_origin.path or parsed_site_origin.query or parsed_site_origin.fragment:
            raise SystemExit('BUILD FAILED: ESICOM_PUBLIC_SITE_URL must be an HTTPS origin, such as https://www.example.com')
    if DIST.exists(): shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    (DIST/'styles.css').write_text(CSS,encoding='utf-8')
    (DIST/'site.js').write_text(JS,encoding='utf-8')
    if (ASSETS/'site-config.js').is_file(): shutil.copy2(ASSETS/'site-config.js', DIST/'site-config.js')
    if ASSETS.exists():
        shutil.copytree(ASSETS,DIST,dirs_exist_ok=True)
    api_base=os.environ.get('ESICOM_API_BASE_URL','').strip().rstrip('/')
    if api_base:
        parsed_api_base=urlsplit(api_base)
        if parsed_api_base.scheme!='https' or not parsed_api_base.netloc or parsed_api_base.path not in ('','/') or parsed_api_base.query or parsed_api_base.fragment:
            raise SystemExit('BUILD FAILED: ESICOM_API_BASE_URL must be an HTTPS origin, such as https://esicom-api.onrender.com')
        (DIST/'site-config.js').write_text(
            'window.ESICOM_API_BASE_URL = '+json.dumps(api_base)+';\n',
            encoding='utf-8',
        )
    for path,data in PAGES.items():
        folder=DIST if path=='/' else DIST/path.strip('/')
        folder.mkdir(parents=True,exist_ok=True)
        (folder/'index.html').write_text(page_html(path,data),encoding='utf-8')
    if SITE_ORIGIN:
        sitemap=''.join(f'<url><loc>{SITE_ORIGIN+path}</loc></url>' for path in PAGES)
        (DIST/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+sitemap+'</urlset>\n',encoding='utf-8')
        (DIST/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+SITE_ORIGIN+'/sitemap.xml\n',encoding='utf-8')
    else:
        (DIST/'robots.txt').write_text('User-agent: *\nAllow: /\n',encoding='utf-8')
    # Build aliases to preserve service-specific routes from the previous project.
    aliases={'/products/office-supplies/':'/office-supplies/','/products/computer-consumables/':'/computer-consumables/','/products/paper-filing/':'/paper-filing/','/services/printing/':'/bulk-printing/','/services/branding/':'/branding/','/services/business-cards/':'/business-cards/','/services/branded-apparel/':'/branded-apparel/','/services/diaries-asset-tags/':'/diaries-asset-tags/','/products/':'/office-supplies/'}
    for alias,target in aliases.items():
        folder=DIST/alias.strip('/'); folder.mkdir(parents=True,exist_ok=True)
        (folder/'index.html').write_text(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={target}"><link rel="canonical" href="{target}"><title>Continue to Esicom Suppliers</title></head><body><p>This page has moved. <a href="{target}">Continue to the relevant page</a>.</p></body></html>',encoding='utf-8')
    # Build gate: all expected pages, key facts, internal targets and assets must exist.
    required=['index.html','office-supplies/index.html','computer-consumables/index.html','bulk-printing/index.html','branding/index.html','about/index.html','contact/index.html','send-file/index.html','file-qr/index.html','catalogue/esicom-suppliers-catalogue.pdf','favicon.svg','images/hero/hero-office-supplies.webp','images/hero/hero-computer.webp','images/hero/hero-printing.webp','images/hero/hero-branding.webp','images/photography/workspace.webp','images/photography/stationery.webp','images/photography/computer.webp','images/photography/printing.webp','images/photography/apparel.webp','images/photography/meeting-room.webp','images/photography/notebook.webp','images/photography/stock-boxed-pens.webp','images/photography/stock-copy-paper.webp','styles.css','site.js']
    missing=[x for x in required if not (DIST/x).is_file()]
    if missing: raise SystemExit('BUILD FAILED: missing files: '+', '.join(missing))
    bad=['10+ years','500+ clients','same-day delivery','nationwide delivery','SME support','authorized distributor','certifications']
    content='\n'.join(p.read_text(errors='ignore') for p in DIST.rglob('*.html')).lower()
    found=[x for x in bad if x in content]
    if found: raise SystemExit('BUILD FAILED: unsupported claims found: '+', '.join(found))
    if '/images/mockups/' in content or 'images.unsplash.com/' in content:
        raise SystemExit('BUILD FAILED: pages must use local photography assets, not mockups or remote photos')
    for path in PAGES:
        p = DIST/'index.html' if path=='/' else DIST/path.strip('/')/'index.html'
        txt=p.read_text()
        if PAGES[path]['kind']=='upload':
            if any(value not in txt for value in ('data-file-upload-form', '15 MB', '50 MB', 'delivery_consent', 'until Esicom staff deletes them')):
                raise SystemExit('BUILD FAILED: file upload page is missing its delivery options, consent, or stated limits.')
            continue
        if PAGES[path]['kind']=='qr':
            if 'data-upload-qr' not in txt or 'data-print-qr' not in txt:
                raise SystemExit('BUILD FAILED: printable file-upload QR page is incomplete.')
            continue
        if 'esicomsuppliers@gmail.com' not in txt or '0728 942 669' not in txt:
            raise SystemExit(f'BUILD FAILED: contact detail missing from {p.relative_to(DIST)}')
        page_key='home' if path=='/' else path.strip('/')
        if f'data-content-page="{page_key}"' not in txt or 'data-copy-image' not in txt:
            raise SystemExit(f'BUILD FAILED: CMS page or hero-image wiring missing from {p.relative_to(DIST)}')
        if PAGES[path]['kind']=='home' and 'data-featured-products' not in txt:
            raise SystemExit('BUILD FAILED: homepage product listing is not CMS-ready')
        if PAGES[path]['kind']=='detail' and 'data-category-products' not in txt:
            raise SystemExit(f'BUILD FAILED: category product listing is not CMS-ready on {p.relative_to(DIST)}')
    print(f'BUILD OK: {len(list(DIST.rglob("index.html")))} HTML pages, catalogue PDF and locally stored photography written to {DIST}')

if __name__=='__main__': main()
