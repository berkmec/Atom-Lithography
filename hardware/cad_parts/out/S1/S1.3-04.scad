// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.3-04)
// ============================================================================
// part_id           : S1.3-04
// parent_bom_id     : S1.3
// subsystem         : S1
// part_name         : Kolon ici cift katmanli mu-metal manyetik kalkan kilifi
// material          : Mu-metal
// temp_stage        : 300 K
// vacuum_grade      : UHV / Dis kilif
// tolerance         : ±0.2 mm cap
// computed_mass_kg  : 1.30722
// envelope_mm       : 124.000 x 124.000 x 162.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 124.0000;
bbox_y = 124.0000;
bbox_z = 162.5000;

// Part-specific parametric dimensions
hi_od = 124.0;
hi_id = 114.0;
lo_od = 108.0;
lo_id = 90.0;
attenuation_dB = 40.0;

// Interface / port parameters (mm)
port_lower_shield_bore_od = 108.000;
port_lower_shield_bore_bore = 90.000;
port_upper_shield_bore_od = 124.000;
port_upper_shield_bore_bore = 114.000;

module part_S1_3_04() {
  union() {
    // Lower outer Mu-metal shield
    translate([0.000, 0.000, -55.500]) {
      difference() {
        cylinder(d=108.000, h=62.000, center=true);
        cylinder(d=104.000, h=64.000, center=true);
      }
    }
    // Lower inner Mu-metal shield
    translate([0.000, 0.000, -55.500]) {
      difference() {
        cylinder(d=94.000, h=62.000, center=true);
        cylinder(d=90.000, h=64.000, center=true);
      }
    }
    // Upper HDA outer Mu-metal shield (R=60.5..62.0)
    translate([0.000, 0.000, 54.000]) {
      difference() {
        cylinder(d=124.000, h=65.000, center=true);
        cylinder(d=121.000, h=67.000, center=true);
      }
    }
    // Upper HDA inner Mu-metal shield (R=57.0..58.5)
    translate([0.000, 0.000, 54.000]) {
      difference() {
        cylinder(d=117.000, h=65.000, center=true);
        cylinder(d=114.000, h=67.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 123.250]) rotate([0.000, 0.000, 0.000]) part_S1_3_04();

part_S1_3_04();
