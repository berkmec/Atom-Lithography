// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S4.2-01)
// ============================================================================
// part_id           : S4.2-01
// parent_bom_id     : S4.2
// subsystem         : S4
// part_name         : Aktif piezo titresim sonumleme tablasi (6-DOF, Herzan/Accurion sinifi)
// material          : Al 6061
// temp_stage        : 300 K
// vacuum_grade      : Atmosfer
// tolerance         : ±0.5 nm artik
// computed_mass_kg  : 35.11084
// envelope_mm       : 820.000 x 620.000 x 60.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 820.0000;
bbox_y = 620.0000;
bbox_z = 60.0000;

// Part-specific parametric dimensions
table_x_mm = 820.0;
table_y_mm = 620.0;
table_h_mm = 60.0;
n_piezo_pods = 6;
dr_bore_d_mm = 420.0;

// Interface / port parameters (mm)
port_uhv_chamber_cf400_seat_od = 456.000;
port_uhv_chamber_cf400_seat_bore = 420.000;

module part_S4_2_01() {
  difference() {
    union() {
      // Active 6-DOF Al-honeycomb top table (820x620x42 mm)
      translate([0.000, 0.000, 9.000]) cube([820.000, 620.000, 42.000], center=true);
      // 6-DOF active piezo actuator cartridge #1
      translate([-330.000, -230.000, -21.100]) cylinder(d=72.000, h=17.800, center=true);
      // 6-DOF active piezo actuator cartridge #2
      translate([330.000, -230.000, -21.100]) cylinder(d=72.000, h=17.800, center=true);
      // 6-DOF active piezo actuator cartridge #3
      translate([330.000, 230.000, -21.100]) cylinder(d=72.000, h=17.800, center=true);
      // 6-DOF active piezo actuator cartridge #4
      translate([-330.000, 230.000, -21.100]) cylinder(d=72.000, h=17.800, center=true);
      // 6-DOF active piezo actuator cartridge #5
      translate([-340.000, 0.000, -21.100]) cylinder(d=72.000, h=17.800, center=true);
      // 6-DOF active piezo actuator cartridge #6
      translate([340.000, 0.000, -21.100]) cylinder(d=72.000, h=17.800, center=true);
    }
    // Central Ø420 mm (R=210 mm) DR clear bore
    translate([0.000, 0.000, 9.000]) cylinder(d=420.000, h=46.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([0.000, 0.000, -270.000]) rotate([0.000, 0.000, 0.000]) part_S4_2_01();

part_S4_2_01();
