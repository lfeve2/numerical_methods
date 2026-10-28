#include "navier-stokes/centered.h"

// Moyenne harmonique pour la viscosité
#define mu(f) (1./(clamp(f,0,1)*(1./mu1 - 1./mu2) + 1./mu2))
#include "two-phase.h"
#include "tension.h"
#include "tracer.h"
#include "diffusion.h"

#define BASE_OUTDIR "output"

#define RHOR 1000.
#define MUR  100.

scalar T[];
scalar * tracers = {T};

double Ga = 50.0;
double Bo = 4.0;
double Pr = 1.0;
int LEVEL = 9;
char casename[128] = "default";
char outdir[1024];

void output_vtu_ascii (scalar * list, vector * vlist, FILE * fp) {
  int ncells = 0;
  foreach() ncells++;
  int npoints = 4 * ncells;

  fprintf (fp, "<?xml version=\"1.0\"?>\n");
  fprintf (fp, "<VTKFile type=\"UnstructuredGrid\" version=\"0.1\" byte_order=\"LittleEndian\">\n");
  fprintf (fp, "  <UnstructuredGrid>\n");
  fprintf (fp, "    <Piece NumberOfPoints=\"%d\" NumberOfCells=\"%d\">\n", npoints, ncells);

  fprintf (fp, "      <Points>\n");
  fprintf (fp, "        <DataArray type=\"Float64\" NumberOfComponents=\"3\" format=\"ascii\">\n");
  foreach() {
    double x0 = x - Delta/2., x1 = x + Delta/2.;
    double y0 = y - Delta/2., y1 = y + Delta/2.;
    fprintf (fp, "          %g %g 0 %g %g 0 %g %g 0 %g %g 0\n",
             x0, y0, x1, y0, x1, y1, x0, y1);
  }
  fprintf (fp, "        </DataArray>\n");
  fprintf (fp, "      </Points>\n");

  fprintf (fp, "      <Cells>\n");
  fprintf (fp, "        <DataArray type=\"Int32\" Name=\"connectivity\" format=\"ascii\">\n");
  for (int i = 0; i < ncells; i++) {
    int o = 4 * i;
    fprintf (fp, "          %d %d %d %d\n", o, o + 1, o + 2, o + 3);
  }
  fprintf (fp, "        </DataArray>\n");
  fprintf (fp, "        <DataArray type=\"Int32\" Name=\"offsets\" format=\"ascii\">\n");
  for (int i = 0; i < ncells; i++) fprintf (fp, "          %d\n", 4 * (i + 1));
  fprintf (fp, "        </DataArray>\n");
  fprintf (fp, "        <DataArray type=\"UInt8\" Name=\"types\" format=\"ascii\">\n");
  for (int i = 0; i < ncells; i++) fprintf (fp, "          9\n");
  fprintf (fp, "        </DataArray>\n");
  fprintf (fp, "      </Cells>\n");

  fprintf (fp, "      <CellData Scalars=\"scalars\">\n");
  for (scalar s in list) {
    fprintf (fp, "        <DataArray type=\"Float64\" Name=\"%s\" format=\"ascii\">\n", s.name);
    foreach() fprintf (fp, "          %g\n", s[]);
    fprintf (fp, "        </DataArray>\n");
  }
  for (vector v in vlist) {
    fprintf (fp, "        <DataArray type=\"Float64\" Name=\"%s\" NumberOfComponents=\"3\" format=\"ascii\">\n", v.x.name);
    foreach() fprintf (fp, "          %g %g 0\n", v.x[], v.y[]);
    fprintf (fp, "        </DataArray>\n");
  }
  fprintf (fp, "      </CellData>\n");
  fprintf (fp, "    </Piece>\n");
  fprintf (fp, "  </UnstructuredGrid>\n");
  fprintf (fp, "</VTKFile>\n");
}

int main (int argc, char * argv[]) {
  if (argc > 1) LEVEL = atoi (argv[1]);
  if (argc > 2) Ga    = atof (argv[2]);
  if (argc > 3) Bo    = atof (argv[3]);
  if (argc > 4) Pr    = atof (argv[4]);
  if (argc > 5) strncpy (casename, argv[5], 127);

  snprintf (outdir, sizeof(outdir), "%s/%s", BASE_OUTDIR, casename);
  char cmd[1100];
  snprintf (cmd, sizeof(cmd), "mkdir -p \"%s\"", outdir);
  system (cmd);

  size (32.0);
  origin (-L0/2., 0.);
  init_grid (64);

  rho1 = 1.;
  rho2 = 1. / RHOR;
  mu1  = 1. / Ga;
  mu2  = 1. / (MUR * Ga);
  f.sigma = 1. / Bo;

  TOLERANCE = 1e-4;
  run();
}

event init (t = 0) {
  refine (sq(x) + sq(y - 2.5) - sq(0.75) < 0 && level < LEVEL);
  fraction (f, sq(x) + sq(y - 2.5) - sq(0.5));

  // Condition initiale physique : bulle chaude (T=1), liquide froid (T=0)
  foreach()
    T[] = 1. - f[];
}

event acceleration (i++) {
  face vector av = a;
  foreach_face(y)
    av.y[] -= 1.;
}

event tracer_diffusion (i++) {
  face vector alpha_d[];
  double alpha1 = 1.0 / (Ga * Pr);
  double alpha2 = alpha1;

  foreach_face() {
    double ff = (f[] + f[-1]) / 2.;
    alpha_d.x[] = ff * alpha1 + (1. - ff) * alpha2;
  }

  diffusion (T, dt, alpha_d);
}

event adapt (i++) {
  double uemax = 1e-2;
  adapt_wavelet ({f, u.x, u.y, T}, (double[]){0.01, uemax, uemax, 0.01}, LEVEL, 4);
}

// 201 snapshots VTU pour animations ParaView fluides
event snapshot_vtu (t = 0; t += 0.1; t <= 18.0) {
  int step = (int) round(t / 0.1);
  char path[1100];
  snprintf (path, sizeof(path), "%s/bubble_%04d.vtu", outdir, step);
  FILE * fp = fopen (path, "w");
  if (fp) {
    output_vtu_ascii ((scalar *){f, T, p}, (vector *){u}, fp);
    fclose (fp);
  }
}

// Extraction robuste par moments d'inertie
event logfile (i += 10; t <= 20.0) {
  double sb = 0.;
  double xb = 0., yb = 0.;
  double vbx = 0., vby = 0.;
  double t_bubble = 0.;
  double max_vort = 0.;

  foreach(reduction(+:xb) reduction(+:yb) 
          reduction(+:vbx) reduction(+:vby) 
          reduction(+:sb) reduction(+:t_bubble)
          reduction(max:max_vort)) {
    double dv = (1. - f[]) * dv();
    sb += dv;
    xb += x * dv;
    yb += y * dv;
    vbx += u.x[] * dv;
    vby += u.y[] * dv;
    t_bubble += T[] * dv;

    double vort = ((u.y[1,0] - u.y[-1,0]) - (u.x[0,1] - u.x[0,-1])) / (2. * Delta);
    if (fabs(vort) > max_vort) max_vort = fabs(vort);
  }

  double inv_sb = (sb > 1e-12) ? (1.0 / sb) : 0.0;
  xb *= inv_sb;
  yb *= inv_sb;
  vbx *= inv_sb;
  vby *= inv_sb;
  t_bubble *= inv_sb;

  double Mxx = 0., Myy = 0.;
  double interfacial_flux = 0.;
  double perimeter = 0.;

  foreach(reduction(+:Mxx) reduction(+:Myy) 
          reduction(+:interfacial_flux) reduction(+:perimeter)) {
    if (f[] < 0.5) {
      double dv = (1. - f[]) * dv();
      Mxx += sq(x - xb) * dv;
      Myy += sq(y - yb) * dv;
    }

    if (f[] > 1e-3 && f[] < 1.0 - 1e-3) {
      coord n = interface_normal (point, f);
      double gradTx = (T[1,0] - T[-1,0]) / (2. * Delta);
      double gradTy = (T[0,1] - T[0,-1]) / (2. * Delta);
      double q_n = fabs(gradTx * n.x + gradTy * n.y);
      interfacial_flux += q_n * Delta;
      perimeter += Delta;
    }
  }

  double aspect_ratio = (Myy > 1e-12) ? sqrt(Mxx / Myy) : 1.0;
  double Nu_mean = (perimeter > 1e-12) ? (interfacial_flux / perimeter) : 0.0;
  double Re = vby * Ga;
  double Pe = Re * Pr;

  fprintf (stderr, "t= %6.3f | Aire= %8.5e | Pos_y= %8.5e | Vel_y= %8.5e | Re= %6.2f | Chi= %6.3f | T_b= %7.4f | Pe= %6.2f | Nu= %6.3f | Vort= %6.2f\n",
           t, sb, yb, vby, Re, aspect_ratio, t_bubble, Pe, Nu_mean, max_vort);
  fflush (stderr);
}