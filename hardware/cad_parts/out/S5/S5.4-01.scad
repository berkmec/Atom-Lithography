// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.4-01)
// ============================================================================
// part_id           : S5.4-01
// parent_bom_id     : S5.4
// subsystem         : S5
// part_name         : Izotopik zenginlestirilmis 28Si/29Si (f=1%) epitaksiyel substrat partisi
// material          : Si
// temp_stage        : 300 K
// vacuum_grade      : Temizoda/UHV
// tolerance         : ±0.1% 29Si
// computed_mass_kg  : 0.00337
// envelope_mm       : 49.678 x 48.685 x 0.775
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 49.6779;
bbox_y = 48.6854;
bbox_z = 0.7750;

// Part-specific parametric dimensions
wafer_od_mm = 50.0;
bom_stock_od_mm = 100.0;
thickness_mm = 0.775;
write_field_mm = 16.0;

// Interface / port parameters (mm)
port_active_epi_top_od = 50.000;
port_active_epi_top_bore = 16.000;
port_carrier_backside_od = 50.000;

module part_S5_4_01() {
  difference() {
    union() {
      // Dia 50 mm 28Si/29Si (f=1%) working wafer substrate
      translate([0.000, 0.000, -0.025]) cylinder(d=50.000, h=0.725, center=true);
      // Active 16x16 mm Arch-B write-field epi mesa (100 nm epi + 8 nm 28Si cap)
      translate([0.000, 0.000, 0.362]) cube([16.000, 16.000, 0.050], center=true);
    }
    // SEMI M1 16.0 mm primary orientation flat
    translate([0.000, -25.185, 0.000]) {
      hull() {
        translate([-8.500, 0, 0]) cylinder(d=3.000, h=1.500, center=true);
        translate([8.500, 0, 0]) cylinder(d=3.000, h=1.500, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, 0.000, 499.613]) rotate([0.000, 0.000, 0.000]) part_S5_4_01();

part_S5_4_01();
