// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S1.1-02)
// ============================================================================
// part_id           : S1.1-02
// parent_bom_id     : S1.1
// subsystem         : S1
// part_name         : Duoplasmatron plazma odasi (29Si+/28Si+ izotop hatti)
// material          : 316LN
// temp_stage        : 300 K (su sogutmali)
// vacuum_grade      : HV 1e-6 mbar (kaynak)
// tolerance         : ±0.05 mm eksen
// computed_mass_kg  : 6.01736
// envelope_mm       : 139.100 x 113.500 x 140.000
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 139.1000;
bbox_y = 113.5000;
bbox_z = 140.0000;

// Part-specific parametric dimensions
body_od = 90.0;
height = 140.0;
x_offset = 165.0;
species = "29Si+/28Si+";

// Interface / port parameters (mm)
port_top_cathode_cf63_od = 113.500;
port_top_cathode_cf63_bore = 40.000;
port_top_cathode_cf63_pcd = 92.100;
port_top_cathode_cf63_bolts = 8;
port_switchover_cf40_neg_x_od = 69.500;
port_switchover_cf40_neg_x_bore = 38.000;
port_switchover_cf40_neg_x_pcd = 58.700;
port_switchover_cf40_neg_x_bolts = 6;
port_sif4_vcr_inlet_od = 14.000;
port_sif4_vcr_inlet_bore = 4.600;

module part_S1_1_02() {
  union() {
    // 316LN water-cooled plasma body
    translate([0.000, 0.000, 0.600]) {
      difference() {
        cylinder(d=90.000, h=102.800, center=true);
        cylinder(d=44.000, h=104.800, center=true);
      }
    }
    // Mo anode extraction cone
    translate([0.000, 0.000, -60.600]) cylinder(d1=28.000, d2=68.000, h=18.800, center=true);
    // Al2O3 HV intermediate insulator
    translate([0.000, 0.000, 2.000]) {
      difference() {
        cylinder(d=42.000, h=52.000, center=true);
        cylinder(d=30.000, h=54.000, center=true);
      }
    }
    // ISO 3669 CF63 cathode flange
    translate([0.000, 0.000, 61.250]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=40.000, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // CF40 isotope switchover port
    translate([-76.000, 0.000, 0.000]) rotate([0.000, -90.000, 0.000]) {
      difference() {
        cylinder(d=69.500, h=12.700, center=true);
        cylinder(d=38.000, h=14.700, center=true);
        translate([0, 0, 5.100]) cylinder(d=48.100, h=1.750);
        for (i = [0 : 6 - 1])
          rotate([0, 0, i * 360 / 6])
            translate([29.350, 0, 0])
              cylinder(d=6.600, h=14.700, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([165.000, 0.000, 492.660]) rotate([0.000, 0.000, 0.000]) part_S1_1_02();

part_S1_1_02();
