// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.4-03)
// ============================================================================
// part_id           : S7.4-03
// parent_bom_id     : S7.4
// subsystem         : S7
// part_name         : 19 inc EMI-kalkanli kontrol/RF kabini ve su/hava isi esanjoru
// material          : Steel
// temp_stage        : 300 K (oda)
// vacuum_grade      : Atmosfer
// tolerance         : ±1 C
// computed_mass_kg  : 310.00000
// envelope_mm       : 1220.000 x 1030.100 x 2049.800
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 1220.0000;
bbox_y = 1030.1000;
bbox_z = 2049.8000;

// Part-specific parametric dimensions
n_cabinets = 2;
rack_u = 42;
cab_w_mm = 600.0;
cab_d_mm = 850.0;
cab_h_mm = 2050.0;
bay_pitch_x_mm = 620.0;
hx_depth_mm = 120.0;

// Interface / port parameters (mm)
port_bay1_cw_supply_od = 32.000;
port_bay1_cw_supply_bore = 22.000;
port_bay2_cw_supply_od = 32.000;
port_bay2_cw_supply_bore = 22.000;

module part_S7_4_03() {
  difference() {
    union() {
      // Bay 1 42U EMI cabinet
      translate([-310.000, 0.000, 0.000]) cube([600.000, 850.000, 2050.000], center=true);
      // Bay 1 rear water/air HX
      translate([-310.000, 490.000, -5.000]) cube([540.000, 120.000, 1920.000], center=true);
      // Bay 2 42U EMI cabinet
      translate([310.000, 0.000, 0.000]) cube([600.000, 850.000, 2050.000], center=true);
      // Bay 2 rear water/air HX
      translate([310.000, 490.000, -5.000]) cube([540.000, 120.000, 1920.000], center=true);
    }
    // Bay 1 open 42U interior
    translate([-310.000, -30.000, -1.500]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-0.000, 0, 0]) cylinder(d=1866.000, h=800.000, center=true);
        translate([0.000, 0, 0]) cylinder(d=1866.000, h=800.000, center=true);
      }
    }
    // Bay 2 open 42U interior
    translate([310.000, -30.000, -1.500]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-0.000, 0, 0]) cylinder(d=1866.000, h=800.000, center=true);
        translate([0.000, 0, 0]) cylinder(d=1866.000, h=800.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([1790.000, 0.000, 1025.000]) rotate([0.000, 0.000, 0.000]) part_S7_4_03();

part_S7_4_03();
