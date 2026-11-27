// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S2.1-01)
// ============================================================================
// part_id           : S2.1-01
// parent_bom_id     : S2.1
// subsystem         : S2
// part_name         : SOI MEMS apertur plakasi (Arch-B es-adimli 0.50 mm, 32x32=1024 demetcik)
// material          : Si
// temp_stage        : 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±50 nm CD, <=2 um egilme
// computed_mass_kg  : 0.00007
// envelope_mm       : 36.000 x 36.000 x 0.030
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 36.0000;
bbox_y = 36.0000;
bbox_z = 0.0300;

// Part-specific parametric dimensions
nx = 32;
ny = 32;
pitch_mm = 0.5;
hole_d_mm = 0.0105;
alpha_land_mrad = 6.4;
sigma_s_nm = 0.5;
soi_t_mm = 0.03;
wafer_od = 36.0;

// Interface / port parameters (mm)
port_beamlet_array_in_od = 36.000;
port_beamlet_array_in_bore = 22.627;
port_beamlet_array_out_od = 36.000;
port_beamlet_array_out_bore = 22.627;

module part_S2_1_01() {
  difference() {
    union() {
      // 30 um highly-doped SOI aperture membrane
      cylinder(d=36.000, h=0.030, center=true);
    }
    // 32x32 = 1,024 Arch-B Ø10.5 um beam-defining apertures
    for (ix = [0 : 32 - 1])
      for (iy = [0 : 32 - 1])
        translate([(ix - 15.500) * 0.5000, (iy - 15.500) * 0.5000, 0])
          cylinder(d=0.0105, h=0.100, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 7.675]) rotate([0.000, 0.000, 0.000]) part_S2_1_01();

part_S2_1_01();
