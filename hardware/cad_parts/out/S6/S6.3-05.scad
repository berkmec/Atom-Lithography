// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.3-05)
// ============================================================================
// part_id           : S6.3-05
// parent_bom_id     : S6.3
// subsystem         : S6
// part_name         : Cift-kutuplu superiletken miknatis guc kaynagi (±300 A) ve >=300 A HTS akim uclari
// material          : Steel
// temp_stage        : 300 K -> 4 K
// vacuum_grade      : Atmosfer/Kriyo
// tolerance         : ±10 ppm, >=300 A
// computed_mass_kg  : 22.60495
// envelope_mm       : 482.600 x 574.550 x 131.350
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 574.5500;
bbox_z = 131.3500;

// Part-specific parametric dimensions
rack_u = 3;
bay = 2;
u_start = 1;
n_hts_pairs = 4;
i_max_a = 320.0;

// Interface / port parameters (mm)

module part_S6_3_05() {
  difference() {
    union() {
      // 19" EIA-310 front bezel panel
      translate([0.000, -268.000, 0.000]) cube([482.600, 4.000, 131.350], center=true);
      // Hollow EMI shielded chassis body
      translate([0.000, 2.050, 0.000]) cube([440.000, 535.900, 130.350], center=true);
    }
    // EIA-310 rack ear slot
    translate([-232.600, -268.000, -42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -268.000, 42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -268.000, -42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -268.000, 42.032]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([-232.600, -268.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
    // EIA-310 rack ear slot
    translate([232.600, -268.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
        translate([1.750, 0, 0]) cylinder(d=6.500, h=6.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([2100.000, 0.000, 156.675]) rotate([0.000, 0.000, 0.000]) part_S6_3_05();

part_S6_3_05();
