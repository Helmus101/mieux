# Audit de l'application existante (étape 1 du plan)

Date : 2026-11-01. Périmètre : `foodiq/` (backend FastAPI, web React/Vite, shared TypeScript). Tests : 28 (pytest), build Vite et tsc OK.

## Pile actuelle vs pile cible
| Élément | Actuel | Cible du plan | Décision |
|---|---|---|---|
| Web | React + Vite + TypeScript | Expo Web | **Conserver** ; la couche `web/src/ui` et `shared/` isolent la plateforme (voir EXPO.md) |
| Mobile | PWA (web) | React Native + Expo | **Plus tard** : réécrire uniquement `ui/index.tsx`, `nav.ts`, scanner, OCR |
| Backend | FastAPI + SQLAlchemy | FastAPI | **Conserver** |
| Base | SQLite (PostgreSQL via `DATABASE_URL`) | PostgreSQL / Supabase | **Corriger** : ajouter Alembic avant la mise en production ; migration actuelle = `_add_missing_columns` (provisoire) |
| Auth | JWT local + session anonyme | Supabase Auth + RLS | **Remplacer en production** ; RLS sans objet tant que la base est locale |
| Données produit | Open Food Facts | Open Food Facts | **Conserver** (isolé dans `off.py`) |
| Prix | Open Prices + tickets + saisie ; devise d'origine conservée ; conversion BCE | + catalogues en ligne | **Conserver** ; catalogues non faits (droits d'accès à vérifier) |
| OCR | Tesseract.js (navigateur) | ML Kit / Vision | **Remplacer** sur mobile |
| Erreurs | logs | Sentry | **À ajouter** |

## Ce qui fonctionne et est testé
Scan + recherche, fiche produit (5 dimensions, NOVA, vitamines), Choice Engine (3 classements, contraintes, restrictions dures), prix par produit avec historique, budget (semaine/mois/course, prévision, catégories), économies potentielles / choisies / réalisées, tickets (OCR, relecture, statuts de correspondance), historique local, export et suppression.

## Écarts avec le plan (honnêtes)
- **Magasins** : volontairement absents du modèle de prix (décision produit). Le plan prévoit `store_id` ; à rouvrir si la comparaison entre enseignes devient un objectif.
- **Catalogues en ligne** : non intégrés.
- **Poids égoutté, promotions « 2 pour 1 », remise globale sur ticket, prix à la pièce** : non gérés.
- **Jeu de référence** (100 produits, 30 paires comparables, 20 non comparables, 30 tickets) : non constitué ; les tests utilisent des données synthétiques.
- **Explications IA** : non faites (le moteur reste 100 % déterministe).
- **Couverture Paris** : dépend d'Open Prices ; pas mesurée.
- **Sécurité** : pas d'audit RLS/pentest ; limitation de débit et CORS en place.

## Prochaines étapes recommandées
1. Alembic + PostgreSQL ; 2. jeu de référence de tickets et de paires ; 3. Sentry ; 4. client Expo (`EXPO.md`) ; 5. étudier les conditions d'accès des catalogues d'enseignes.
