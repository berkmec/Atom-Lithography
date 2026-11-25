// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.4-03)
// ============================================================================
// part_id           : S5.4-03
// parent_bom_id     : S5.4
// subsystem         : S5
// part_name         : UHV/N2 purjlu yonga tasima podlari ve depolama kabini
// material          : 304 SS
// temp_stage        : 300 K
// vacuum_grade      : N2 atmosferi
// tolerance         : <1 ppm O2/H2O
// computed_mass_kg  : 41.97232
// envelope_mm       : 380.000 x 383.000 x 690.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 380.0000;
bbox_y = 383.0000;
bbox_z = 690.8000;

// Part-specific parametric dimensions
cab_w = 380.0;
cab_d = 340.0;
cab_h = 516.0;
foup_w = 180.0;

// Interface / port parameters (mm)

module part_S5_4_03() {
  difference() {
    union() {
      // 304 SS dry-N2 wafer storage cabinet
      translate([0.000, 0.000, 282.000]) cube([380.000, 340.000, 516.000], center=true);
      // PFA N2-purged FOUP transfer pod
      translate([0.000, 0.000, 609.500]) cube([180.000, 170.000, 138.000], center=true);
      // SEMI E47.1 top robotic grip flange
      translate([0.000, 0.000, 684.800]) cube([68.000, 68.000, 12.000], center=true);
    }
    // N2 purge gas inlet
    translate([-110.000, 170.000, 460.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=12.000, h=40.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([780.000, -900.000, 0.000]) rotate([0.000, 0.000, 0.000]) part_S5_4_03();

part_S5_4_03();
