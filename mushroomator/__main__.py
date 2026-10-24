"""Command line: python -m mushroomator <command>."""
import argparse
import datetime as dt
import functools
import http.server

from .config import DEFAULT_REGION, REGIONS, SITE_DIR


def cmd_layers(args):
    from . import layers
    layers.build(args.region)


def cmd_train(args):
    from . import habitat, trigger, weather
    from .sources import eobs
    region = REGIONS[args.region]
    eo = eobs.load()
    weather.build_swb_climatology(region, eo)
    species = habitat.load_species()
    for key in args.species or species:
        print(f"Espèce : {species[key]['nom']}")
        trigger.train(key, species[key], eo, region.bbox)


def cmd_validate(args):
    from . import validation
    validation.run(args.region)
    validation.hindcast(args.region)


def cmd_update(args):
    from . import site, weather
    region = REGIONS[args.region]
    day = dt.date.fromisoformat(args.day) if args.day else None
    if args.replay_eobs:
        from .sources import eobs
        raw = weather.replay_eobs(region, dt.date.fromisoformat(args.replay_eobs), eobs.load())
    else:
        raw = weather.fetch(region, day, force=args.force)
    site.build(args.region, weather.export(region, raw))


def cmd_site(args):
    from . import site
    site.build(args.region)


def cmd_serve(args):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE_DIR))
    with http.server.ThreadingHTTPServer((args.host, args.port), handler) as httpd:
        print(f"Mushroomator : http://{args.host}:{args.port}/  (Ctrl+C pour arrêter)")
        httpd.serve_forever()


def main(argv=None):
    p = argparse.ArgumentParser(prog="mushroomator", description="Carte de chaleur des champignons comestibles.")
    p.add_argument("--region", default=DEFAULT_REGION, choices=sorted(REGIONS))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("layers", help="construire les couches statiques (forêts, relief, sol) — long, une seule fois").set_defaults(func=cmd_layers)
    t = sub.add_parser("train", help="entraîner les modèles météo (E-OBS + GBIF)")
    t.add_argument("--species", nargs="*", help="clés d'espèces (défaut : toutes)")
    t.set_defaults(func=cmd_train)
    sub.add_parser("validate", help="valider l'habitat et rejouer les saisons passées sur les observations de la région").set_defaults(func=cmd_validate)
    u = sub.add_parser("update", help="télécharger la météo du jour et régénérer le site")
    u.add_argument("--day", help="date de référence AAAA-MM-JJ (défaut : aujourd'hui)")
    u.add_argument("--force", action="store_true", help="ignorer le cache météo du jour")
    u.add_argument("--replay-eobs", metavar="AAAA-MM-JJ", help="rejouer une date passée avec E-OBS (≤ 06/2024)")
    u.set_defaults(func=cmd_update)
    sub.add_parser("site", help="régénérer le site sans nouvelle météo").set_defaults(func=cmd_site)
    s = sub.add_parser("serve", help="servir le site en local")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(func=cmd_serve)
    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
