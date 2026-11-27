// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.11-02)
// ============================================================================
// part_id           : S6.11-02
// parent_bom_id     : S6.11
// subsystem         : S6
// part_name         : 20 mK Josephson TWPA + Bant-Geciren Purcell Filtre + Cift Kriyo-Izolator (32 hat, Exp140 S6.5-02, 2.72 kg)
// material          : Nb
// temp_stage        : 20 mK (MXC)
// vacuum_grade      : Kriyo-vakum
// tolerance         : F_RO>=0.995
// computed_mass_kg  : 2.82690
// envelope_mm       : 180.000 x 140.000 x 55.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 180.0000;
bbox_y = 140.0000;
bbox_z = 55.0000;

// Part-specific parametric dimensions
n_twpa = 32;
box_dx = 180.0;
box_dy = 140.0;
box_dz = 55.0;
pocket_xy_mm = 14.0;
pocket_z_mm = 44.8;
f_te101_ghz = 11.22;
eccosorb_liner_mm = 0.9;
p_20mk_uw = 2.144;

// Interface / port parameters (mm)
port_mxc_20mk_mount_bolts = 4;

module part_S6_11_02() {
  difference() {
    union() {
      // 32x 20 mK TWPA + Purcell partitioned Nb/Cryoperm magnetic shield box
      cube([180.000, 140.000, 55.000], center=true);
    }
    // 32x 14x14 mm sub-cutoff RF pockets (f_TE101=11.22 GHz)
    for (ix = [0 : 8 - 1])
      for (iy = [0 : 4 - 1])
        translate([(ix - 3.500) * 18.0000, (iy - 1.500) * 22.0000, 0])
          cylinder(d=14.0000, h=44.800, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 452.000]) rotate([0.000, 0.000, 0.000]) part_S6_11_02();

part_S6_11_02();
