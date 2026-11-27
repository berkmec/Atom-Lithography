// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.6-02)
// ============================================================================
// part_id           : S5.6-02
// parent_bom_id     : S5.6
// subsystem         : S5
// part_name         : Zenginlestirilmis 28Si cubuk (<50 ppm 29Si, >1000 yonga) + UHV QCM kalinlik izleme & vana (Exp139, 3.4 kg)
// material          : 316LN
// temp_stage        : 300 K
// vacuum_grade      : UHV 1.5e-10 Torr
// tolerance         : <50 ppm 29Si, ±0.3 nm
// computed_mass_kg  : 2.01225
// envelope_mm       : 83.750 x 120.200 x 87.250
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 83.7500;
bbox_y = 120.2000;
bbox_z = 87.2500;

// Part-specific parametric dimensions
qcm_freq_MHz = 6.0;
cap_tol_nm = 0.3;
si29_ppm_max = 50;

// Interface / port parameters (mm)
port_mbe_qcm_cf40_mate_od = 69.500;
port_mbe_qcm_cf40_mate_bore = 38.000;
port_mbe_qcm_cf40_mate_pcd = 58.700;
port_mbe_qcm_cf40_mate_bolts = 6;

module part_S5_6_02() {
  union() {
    // Mating CF40 flange on S5.6-01 -Y port
    translate([0.000, -6.350, 0.000]) rotate([-90.000, 0.000, 0.000]) {
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
    // All-metal UHV QCM isolation valve
    translate([0.000, -32.000, 0.000]) cube([50.000, 38.000, 68.000], center=true);
    // 6 MHz QCM water-cooled sensor head
    translate([0.000, -81.000, 0.000]) rotate([90.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=30.000, h=34.000, center=true);
        cylinder(d=22.000, h=36.000, center=true);
      }
    }
    // Enriched 28Si (<50 ppm 29Si) feedstock rod canister
    translate([36.000, -32.000, 0.000]) cylinder(d=18.000, h=62.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, -88.500, 705.000]) rotate([0.000, 0.000, 0.000]) part_S5_6_02();

part_S5_6_02();
