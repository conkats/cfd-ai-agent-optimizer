/*============================================================================
 * General-purpose user-defined functions called before time stepping, at
 * the end of each time step, and after time-stepping.
 *
 * These can be used for operations which do not fit naturally in any other
 * dedicated user function.
 *============================================================================*/

/* VERS */

/*
  This file is part of code_saturne, a general-purpose CFD tool.

  Copyright (C) 1998-2022 EDF S.A.

  This program is free software; you can redistribute it and/or modify it under
  the terms of the GNU General Public License as published by the Free Software
  Foundation; either version 2 of the License, or (at your option) any later
  version.

  This program is distributed in the hope that it will be useful, but WITHOUT
  ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
  FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
  details.

  You should have received a copy of the GNU General Public License along with
  this program; if not, write to the Free Software Foundation, Inc., 51 Franklin
  Street, Fifth Floor, Boston, MA 02110-1301, USA.
*/

/*----------------------------------------------------------------------------*/

#include "cs_defs.h"

/*----------------------------------------------------------------------------
 * Standard C library headers
 *----------------------------------------------------------------------------*/

#include <assert.h>
#include <math.h>

#if defined(HAVE_MPI)
#include <mpi.h>
#endif

/*----------------------------------------------------------------------------
 * PLE library headers
 *----------------------------------------------------------------------------*/

#include <ple_coupling.h>

/*----------------------------------------------------------------------------
 * Local headers
 *----------------------------------------------------------------------------*/

#include "cs_headers.h"

/*----------------------------------------------------------------------------*/

BEGIN_C_DECLS

/*----------------------------------------------------------------------------*/
/*!
 * \file cs_user_extra_operations.c
 *
 * \brief This function is called at the end of each time step, and has a very
 * general purpose (i.e. anything that does not have another dedicated
 * user function)
 */
/*----------------------------------------------------------------------------*/

/*============================================================================
 * User function definitions
 *============================================================================*/

/*----------------------------------------------------------------------------*/
/*!
 * \brief This function is called at the end of each time step.
 *
 * It has a very general purpose, although it is recommended to handle
 * mainly postprocessing or data-extraction type operations.
 *
 * \param[in, out]  domain   pointer to a cs_domain_t structure
 */
/*----------------------------------------------------------------------------*/

void
cs_user_extra_operations(cs_domain_t     *domain)
{
  const cs_mesh_t *mesh = domain->mesh;
  const cs_mesh_quantities_t *mq = domain->mesh_quantities;
  cs_time_step_t *ts = domain->time_step;

  const cs_lnum_t    *b_face_cells = mesh->b_face_cells;
  const cs_real_3_t  *b_face_normal = (const cs_real_3_t *)mq->b_face_normal;

  const int n_period_stats = 12;

  static FILE *cf = NULL;
  static double usr_efforts[2] = {0, 0};  /* z efforts at time n-1, n-2 */
  static double amplitude[12]; /* saved period, cycle */
  static double t_perio[12];   /* physical time for each period end */
  static double d_perio[12];   /* duration for each period */
  static double f_min = HUGE_VAL;
  static int n_periods = 0, n_init_periods = 0;

  /* Open file at first call */

  if (cf == NULL && cs_glob_rank_id < 1) {
    cf = fopen("pressure_coefficient.csv", "w");
    fprintf(cf, "ntcabs, ttcabs, Fx, Fy, Fz\n");
  }

  /* Boundary faces selection */

  const cs_zone_t  *z = cs_boundary_zone_by_name("cylindre");

  /* Pressure field */

  const cs_field_t  *f = CS_F_(p);

  const cs_real_t *coefa = f->bc_coeffs->a;
  const cs_real_t *coefb = f->bc_coeffs->b;
  const cs_real_t *cvar_pr = f->val;

  /* Compute pressure forces */

  cs_real_t p_force[3] = {0, 0, 0};

  for (cs_lnum_t i = 0; i < z->n_elts; i++) {
    cs_lnum_t face_id = z->elt_ids[i];
    cs_real_t pfac =   coefa[face_id]
                     + coefb[face_id] * cvar_pr[b_face_cells[face_id]];
    for (cs_lnum_t j = 0; j < 3; j++)
      p_force[j] += pfac*b_face_normal[face_id][j];
  }

  cs_parall_sum(3, CS_REAL_TYPE, p_force);

  /* Detect min/max — auto-stop logic DISABLED for shape-comparison runs
     (we want a fixed 2000-iteration sample for fair comparison). */

#if 0
  double v1 = p_force[2] - usr_efforts[0];
  double v2 = usr_efforts[0] - usr_efforts[1];

  if (v1*v2 < 0 && fabs(usr_efforts[0]) > 0.05) {
    if (cs_glob_rank_id < 1)
      bft_printf("\nWall force inversion, Fz = %g\n", p_force[2]);

    if (p_force[2] < 0)
      f_min = p_force[2];
    else if (f_min < 0) {
      int i_s = n_periods % n_period_stats;
      amplitude[i_s] = p_force[2] - f_min;
      t_perio[i_s] = ts->t_cur;
      if (n_periods > 1)
        d_perio[i_s] = ts->t_cur - t_perio[(n_periods-1) % n_period_stats];

      if (n_periods > n_period_stats) {
        double a_min = amplitude[0];
        for (int j = 1; j < n_period_stats; j++) {
          if (amplitude[j] < a_min)
            a_min = amplitude[j];
        }
        double a_ratio = fabs(amplitude[i_s]/a_min);
        if (cs_glob_rank_id < 1)
          bft_printf("  amplitude: %g; ratio to previous: %g\n\n",
                     amplitude[i_s], a_ratio);

        if (a_ratio > 1.05)
          n_init_periods = n_periods;
        else if (n_periods - n_init_periods > n_period_stats) {
          ts->nt_max = ts->nt_cur + 1;
        }
      }
      n_periods += 1;
    }
  }
#endif
  /* Silence unused-variable warnings now that auto-stop is disabled. */
  (void)usr_efforts;
  (void)amplitude;
  (void)t_perio;
  (void)d_perio;
  (void)f_min;
  (void)n_init_periods;
  (void)n_period_stats;

  /* Update */

  usr_efforts[1] = usr_efforts[0];
  usr_efforts[0] = p_force[2];

  /* Write to file */

  if (cf != NULL)
    fprintf(cf, "%10d, %17.9e, %17.9e, %17.9e, %17.9e\n",
            ts->nt_cur, ts->t_cur, p_force[0], p_force[1], p_force[2]);

  /* Close file at end */

  if (cf != NULL && ts->nt_cur == ts->nt_max) {
    fclose(cf);
    cf = NULL;
  }

  /* Also compute amplitude and period */

  if (ts->nt_cur == ts->nt_max) {
    bft_printf("\n"
               "Detected oscillation periods: %d\n"
               "----------------------------\n\n",
               n_periods);

    int _n_period_stats = n_period_stats;
    if (n_periods < _n_period_stats)
      _n_period_stats = n_periods;

    int s_id = 0;
    for (int j = 1; j < _n_period_stats; j++) {
      if (t_perio[j] < t_perio[j-1]) {
        s_id = j;
        break;
      }
    }
    double a_max = -HUGE_VAL, d_max = -HUGE_VAL;
    double a_min = HUGE_VAL, d_min = HUGE_VAL;
    double a_mean = 0, d_mean = 0;

    for (int i = 0; i < _n_period_stats; i++) {
      int j0 = (s_id + i) % n_period_stats;
      double a = amplitude[j0];
      double d = d_perio[j0];
      if (a < a_min)
        a_min = a;
      else if (a > a_max)
        a_max = a;
      if (d < d_min)
        d_min = d;
      else if (d > d_max)
        d_max = d;
      a_mean += a;
      d_mean += d;
      bft_printf("  %2d: %10.5f s (start %10.5f), amplitude %g\n",
                       i, d_perio[j0], t_perio[j0], a);
    }

    if (_n_period_stats > 0) {
      a_mean /= _n_period_stats;
      d_mean /= _n_period_stats;

      const cs_fluid_properties_t  *fp = cs_glob_fluid_properties;
      const double rho = fp->ro0;
      double dia = 0.5;
      double vel = 1.0;

      double freq = 1./d_mean;
      double strouhal = freq * dia / vel;

      bft_printf("\n"
                 "  Amplitude: %g (%g min, %g max)\n"
                 "  Interval:  %g (%g min, %g max)\n\n"
                 "  Strouhal number: \n\n",
                 a_mean, a_min, a_max, d_mean, d_min, d_max,
                 strouhal);
    }
  }
}

/*----------------------------------------------------------------------------*/

END_C_DECLS
