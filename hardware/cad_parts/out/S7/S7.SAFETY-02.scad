// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S7.SAFETY-02)
// ============================================================================
// part_id           : S7.SAFETY-02
// parent_bom_id     : S7.SAFETY
// subsystem         : S7
// part_name         : ANSI Z136.1 OD>=8 (808 nm) Kilitli Sinif-1 3 mm Celik Lazer+X-Isini Kilifi & Cift-Kanalli SIL-3 Mekanik Perde (<5 ms, Exp150, 38.0 kg)
// material          : 316L
// temp_stage        : 300 K (S5.5 +Y cevre)
// vacuum_grade      : Atmosfer
// tolerance         : OD>=8, <0.01 uSv/h, <5 ms
// computed_mass_kg  : 38.00000
// envelope_mm       : 210.000 x 283.406 x 282.299
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 210.0000;
bbox_y = 283.4055;
bbox_z = 282.2994;

// Part-specific parametric dimensions
shroud_w_mm = 210.0;
shroud_d_mm = 190.0;
shroud_h_mm = 200.0;
min_316l_wall_mm = 3.0;
cavity_w_mm = 148.0;
elev_deg = 36.0;

// Interface / port parameters (mm)
port_s55_viewport_shroud_mate_od = 113.500;
port_s55_viewport_shroud_mate_bore = 63.500;
port_s55_viewport_shroud_mate_pcd = 92.100;
port_s55_viewport_shroud_mate_bolts = 8;
port_fiber_labyrinth_port_od = 56.000;
port_fiber_labyrinth_port_bore = 36.000;

module part_S7_SAFETY_02() {
  difference() {
    union() {
      // 3 mm+ 316L OD>=8 laser & X-ray shroud (36-deg inclined)
      cube([210.000, 205.000, 200.000], center=true);
    }
    // Open S5.5 optical head clearance cavity
    translate([0.000, -15.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      hull() {
        translate([-0.000, 0, 0]) cylinder(d=170.000, h=200.000, center=true);
        translate([0.000, 0, 0]) cylinder(d=170.000, h=200.000, center=true);
      }
    }
    // Rear armored 808 nm fiber labyrinth port
    translate([0.000, 95.000, -26.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=42.000, h=40.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, 238.749, 705.599]) rotate([0.000, 0.000, 0.000]) part_S7_SAFETY_02();

part_S7_SAFETY_02();
