// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.6-03)
// ============================================================================
// part_id           : S5.6-03
// parent_bom_id     : S5.6
// subsystem         : S5
// part_name         : Yuk-kilidi 345 C pirolitik-BN radyatif isitici + 350 C %5 H2/N2 FG/atomik-H pasivasyon manifoldu (Exp139, 4.2 kg)
// material          : 316L
// temp_stage        : 300-723 K (yuk-kilidi)
// vacuum_grade      : UHV / FG-H
// tolerance         : ±2 C PID
// computed_mass_kg  : 2.73756
// envelope_mm       : 93.950 x 120.000 x 103.750
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 93.9500;
bbox_y = 120.0000;
bbox_z = 103.7500;

// Part-specific parametric dimensions
t_epi_C = 345.0;
t_fg_C = 350.0;
heater_power_W = 150.0;

// Interface / port parameters (mm)
port_mbe_pbn_cf40_mate_od = 69.500;
port_mbe_pbn_cf40_mate_bore = 38.000;
port_mbe_pbn_cf40_mate_pcd = 58.700;
port_mbe_pbn_cf40_mate_bolts = 6;

module part_S5_6_03() {
  union() {
    // Mating CF40 flange on S5.6-01 310 deg port
    translate([0.000, 6.350, 0.000]) rotate([90.000, 0.000, 0.000]) {
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
    // 316L VAR PBN heater & forming-gas manifold
    translate([0.000, 38.000, 0.000]) cube([54.000, 50.000, 68.000], center=true);
    // Top CF40 345 C PBN heater power/TC feedthrough
    translate([0.000, 38.000, 40.500]) {
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
    // Precision sapphire-seat 5% H2/N2 leak valve
    translate([0.000, 92.000, 0.000]) rotate([90.000, 0.000, 0.000]) cylinder(d=50.000, h=56.000, center=true);
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([360.782, -65.768, 733.500]) rotate([0.000, 0.000, 138.000]) part_S5_6_03();

part_S5_6_03();
