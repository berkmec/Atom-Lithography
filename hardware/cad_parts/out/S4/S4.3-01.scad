// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.3-01)
// ============================================================================
// part_id           : S4.3-01
// parent_bom_id     : S4.3
// subsystem         : S4
// part_name         : 6-DOF UHV ince piezo flekstur kademesi (PI PIMars P-562/563 UHV sinifi)
// material          : Ti-6Al-4V
// temp_stage        : 300 K (UHV)
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : ±0.2 nm RMS
// computed_mass_kg  : 0.62838
// envelope_mm       : 90.000 x 90.000 x 24.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 90.0000;
bbox_y = 90.0000;
bbox_z = 24.0000;

// Part-specific parametric dimensions
stage_xy_mm = 90.0;
stage_h_mm = 24.0;
stroke_um = 200.0;
n_flexure_slots = 8;
bore_d_mm = 36.0;

// Interface / port parameters (mm)
port_vespel_standoff_deck_bore = 36.000;
port_coarse_stage_mount_bolts = 4;

module part_S4_3_01() {
  difference() {
    union() {
      // Ti-6Al-4V monolithic EDM flexure body (90x90x19 mm)
      translate([0.000, 0.000, -2.500]) cube([90.000, 90.000, 19.000], center=true);
      // Invar-36 6-DOF moving stage platform
      translate([0.000, 0.000, 9.600]) cube([76.000, 76.000, 4.800], center=true);
    }
    // Central Ø36 mm axial clear aperture
    cylinder(d=36.000, h=28.000, center=true);
    // EDM flexure hinge cutout #1
    translate([0.000, 35.000, -2.500]) {
      hull() {
        translate([-21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
        translate([21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #2
    translate([0.000, -35.000, -2.500]) {
      hull() {
        translate([-21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
        translate([21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #3
    translate([35.000, 0.000, -2.500]) rotate([0.000, 0.000, 90.000]) {
      hull() {
        translate([-21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
        translate([21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #4
    translate([-35.000, 0.000, -2.500]) rotate([0.000, 0.000, 90.000]) {
      hull() {
        translate([-21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
        translate([21.600, 0, 0]) cylinder(d=2.800, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #5
    translate([0.000, 25.000, -2.500]) {
      hull() {
        translate([-10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
        translate([10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #6
    translate([0.000, -25.000, -2.500]) {
      hull() {
        translate([-10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
        translate([10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #7
    translate([25.000, 0.000, -2.500]) rotate([0.000, 0.000, 90.000]) {
      hull() {
        translate([-10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
        translate([10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
      }
    }
    // EDM flexure hinge cutout #8
    translate([-25.000, 0.000, -2.500]) rotate([0.000, 0.000, 90.000]) {
      hull() {
        translate([-10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
        translate([10.800, 0, 0]) cylinder(d=2.400, h=22.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -41.000]) rotate([0.000, 0.000, 0.000]) part_S4_3_01();

part_S4_3_01();
