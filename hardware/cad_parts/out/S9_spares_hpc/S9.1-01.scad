// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S9.1-01)
// ============================================================================
// part_id           : S9.1-01
// parent_bom_id     : S9.1
// subsystem         : S9
// part_name         : Bilinen donor desenli kalibrasyon referans yongalari (5 yonga)
// material          : Si
// temp_stage        : 20 mK - 300 K
// vacuum_grade      : UHV 1e-9 mbar
// tolerance         : Bilinen doz ±2%
// computed_mass_kg  : 1.45000
// envelope_mm       : 188.800 x 136.400 x 92.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 188.8000;
bbox_y = 136.4000;
bbox_z = 92.0000;

// Part-specific parametric dimensions
qty_wafers = 5;
wafer_od_mm = 50.0;
case_dx_mm = 160.0;
case_dy_mm = 120.0;

// Interface / port parameters (mm)
port_wafer_carrier_slot_bore = 50.000;

module part_S9_1_01() {
  difference() {
    union() {
      // Cleanroom ESD storage case outer envelope
      cube([160.000, 120.000, 92.000], center=true);
    }
    // Internal padded kit tray cavity
    hull() {
      translate([-20.000, 0, 0]) cylinder(d=104.000, h=61.400, center=true);
      translate([20.000, 0, 0]) cylinder(d=104.000, h=61.400, center=true);
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-900.000, -1180.000, 46.000]) rotate([0.000, 0.000, 0.000]) part_S9_1_01();

part_S9_1_01();
