# Direct Numerical Simulation (DNS) of Rising Vapor Bubbles with Thermal Convection and Phase Change

Ce dépôt héberge le framework de simulation numérique directe, d'automatisation et de post-traitement dédié à l'ascension de bulles déformables dans un milieu liquide sous-refroidi. Le projet est développé sous l'environnement **Basilisk C** et s'appuie sur une décomposition physique en trois niveaux progressifs :
1. **Niveau 1** : Hydrodynamique diphasique incompressible et régimes de déformation.
2. **Niveau 2** : Convection-diffusion thermique et lois d'échelle de transfert à l'interface.
3. **Niveau 3** : Changement de phase liquide-vapeur avec condensation et contraction volumique.

---

## Sommaire
- [Architecture du projet](#architecture-du-projet)
- [Cadre physique et adimensionnement](#cadre-physique-et-adimensionnement)
- [Détail des modèles et implémentation numérique](#détail-des-modèles-et-implémentation-numérique)
  - [Niveau 1 : Écoulement diphasique & VOF-PLIC](#1-niveau-1--écoulement-diphasique--vof-plic)
  - [Niveau 2 : Transport thermique convectif (`level2_thermal.c`)](#2-niveau-2--transport-thermique-convectif-level2_thermalc)
  - [Niveau 3 : Changement de phase et condition de Stefan (`level3_phase_change.c`)](#3-niveau-3--changement-de-phase-et-condition-de-stefan-level3_phase_changec)
- [Résolution des verrous numériques](#résolution-des-verrous-numériques)
- [Métriques d'extraction et post-traitement](#métriques-dextraction-et-post-traitement)
- [Guide d'utilisation et exécution](#guide-dutilisation-et-exécution)
  - [Compilation unitaire](#compilation-unitaire)
  - [Campagnes automatisées (`run_campaign.py`)](#campagnes-automatisées-run_campaignpy)
  - [Étude de convergence spatiale (`run_convergence.py`)](#étude-de-convergence-spatiale-run_convergencepy)
  - [Visualisation sous ParaView](#visualisation-sous-paraview)

---

## Architecture du projet

```text
numerical_methods/
├── level2_thermal.c       # Solveur C Basilisk : hydrodynamique diphasique + scalaire passif thermique
├── level3_phase_change.c  # Solveur C Basilisk : couplage Stefan + condensation quasi-isochore
├── run_campaign.py        # Orchestrateur Python : balayages multiparamétriques (Ga, Bo, Pr, Ja)
├── run_convergence.py     # Script d'analyse de convergence spatiale (niveaux de grille 8 à 11)
├── doe_lvl2_logs/         # Données brutes de diagnostic générées lors des simulations
├── lvl1_aspect_ratio*.png # Tracés post-traités : rapport d'aspect vs temps et diagramme de Grace
├── lvl1_velocity*.png     # Tracés post-traités : profils temporels de vitesse terminale
├── lvl2_boundary_layer.png# Tracé : mise à l'échelle de l'épaisseur de couche limite thermique
├── lvl2_cooling.png       # Tracé : cinétique de refroidissement du cœur de bulle T_b(t*)
├── .gitignore             # Exclusion des artéfacts de compilation, fichiers VTU et logs lourds
└── README.md              # Documentation technique et scientifique du projet