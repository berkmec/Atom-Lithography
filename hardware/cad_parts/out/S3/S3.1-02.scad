// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S3.1-02)
// ============================================================================
// part_id           : S3.1-02
// parent_bom_id     : S3.1
// subsystem         : S3
// part_name         : Koruma halkasi (guard-ring) ve arka-yuzey ohmik metalizasyon + tel-bag
// material          : Au
// temp_stage        : 20 mK - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : <1 Ohm kontak
// computed_mass_kg  : 0.00299
// envelope_mm       : 52.824 x 53.156 x 0.720
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 52.8237;
bbox_y = 53.1561;
bbox_z = 0.7200;

// Part-specific parametric dimensions
n_guard_rings = 3;
n_wirebond_tabs = 16;
ohmic_od_mm = 46.0;

// Interface / port parameters (mm)
port_wirebond_pad_ring_od = 56.800;
port_wirebond_pad_ring_bore = 50.600;
port_rear_ohmic_bias_od = 46.000;

module part_S3_1_02() {
  union() {
    // Inner Al/Ti/Au guard ring #1
    translate([0.000, 0.000, -0.020]) {
      difference() {
        cylinder(d=41.400, h=0.080, center=true);
        cylinder(d=40.600, h=2.080, center=true);
      }
    }
    // Middle Al/Ti/Au guard ring #2
    translate([0.000, 0.000, -0.020]) {
      difference() {
        cylinder(d=43.000, h=0.080, center=true);
        cylinder(d=42.200, h=2.080, center=true);
      }
    }
    // Outer Al/Ti/Au guard ring #3
    translate([0.000, 0.000, -0.020]) {
      difference() {
        cylinder(d=44.600, h=0.080, center=true);
        cylinder(d=43.800, h=2.080, center=true);
      }
    }
    // Rear ohmic bias metallization
    translate([0.000, 0.000, -0.600]) cylinder(d=46.000, h=0.080, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, 0.000]) rotate([0.000, 0.000, 0.000]) part_S3_1_02();

part_S3_1_02();
