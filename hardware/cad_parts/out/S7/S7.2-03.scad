// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.2-03)
// ============================================================================
// part_id           : S7.2-03
// parent_bom_id     : S7.2
// subsystem         : S7
// part_name         : PXIe / AXIe dusuk-gurultulu enstruman sasisi ve arka-panel
// material          : Al 6061
// temp_stage        : 300 K (kabin)
// vacuum_grade      : Atmosfer
// tolerance         : <1 ps skew
// computed_mass_kg  : 16.50000
// envelope_mm       : 482.600 x 536.100 x 175.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 482.6000;
bbox_y = 536.1000;
bbox_z = 175.8000;

// Part-specific parametric dimensions
u_start = 10;
u_count = 4;
slots = 18;
slot_pitch_mm = 20.32;

// Interface / port parameters (mm)

module part_S7_2_03() {
  difference() {
    union() {
      // PXIe 4U chassis outer body
      cube([440.000, 520.000, 175.800], center=true);
      // 19-inch front mounting ears
      translate([0.000, -257.750, 0.000]) cube([482.600, 4.500, 175.800], center=true);
    }
    // 18-slot open PXIe card bay
    translate([0.000, -45.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-126.500, 0, 0]) cylinder(d=139.000, h=432.000, center=true);
        translate([126.500, 0, 0]) cylinder(d=139.000, h=432.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1480.000, -178.000, 578.950]) rotate([0.000, 0.000, 0.000]) part_S7_2_03();

part_S7_2_03();
