// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.9-01)
// ============================================================================
// part_id           : S6.9-01
// parent_bom_id     : S6.9
// subsystem         : S6
// part_name         : PT420 500 mm ofsetli uzak doner valf kutusu ve L=600 mm esnek He yuksek-basinc hatti (Exp133)
// material          : Al 6061
// temp_stage        : 300 K (tesis)
// vacuum_grade      : 20 bar He
// tolerance         : 20 bar He, He<=1e-9
// computed_mass_kg  : 42.50762
// envelope_mm       : 533.000 x 220.000 x 1190.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 533.0000;
bbox_y = 220.0000;
bbox_z = 1190.0000;

// Part-specific parametric dimensions
valve_offset_mm = 500.0;
flex_he_length_mm = 600.0;
box_dx = 180.0;
box_dy = 160.0;
box_dz = 180.0;

// Interface / port parameters (mm)
port_he_uloop_to_pt420_od = 21.000;
port_he_uloop_to_pt420_bore = 15.000;
port_floor_anchor_base_bolts = 4;

module part_S6_9_01() {
  union() {
    // Acoustic floor stand
    translate([0.000, 0.000, -99.500]) cube([160.000, 160.000, 996.000], center=true);
    // PT420 500 mm offset acoustic valve box
    translate([0.000, 0.000, 490.000]) cube([180.000, 160.000, 180.000], center=true);
    // 600 mm braided He U-loop envelope
    translate([257.000, 0.000, 458.000]) rotate([0.000, 90.000, 0.000]) cylinder(d=21.000, h=332.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-1150.000, 0.000, 610.000]) rotate([0.000, 0.000, 0.000]) part_S6_9_01();

part_S6_9_01();
