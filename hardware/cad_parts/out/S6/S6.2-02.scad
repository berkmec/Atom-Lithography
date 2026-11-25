// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.2-02)
// ============================================================================
// part_id           : S6.2-02
// parent_bom_id     : S6.2
// subsystem         : S6
// part_name         : Altin kapli 50 K / 4 K / Still radyasyon kalkanlari ve MLI battaniyeleri
// material          : OFHC Cu
// temp_stage        : 50 K / 4 K / 0.8 K
// vacuum_grade      : UHV / Kriyo-vakum
// tolerance         : ±0.2 mm
// computed_mass_kg  : 22.88405
// envelope_mm       : 742.000 x 316.000 x 623.750
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 742.0000;
bbox_y = 316.0000;
bbox_z = 623.7500;

// Part-specific parametric dimensions
r50_in = 150.0;
r50_out = 154.0;
r4_in = 132.0;
r4_out = 136.0;
rstill_in = 116.0;
rstill_out = 119.0;

// Interface / port parameters (mm)
port_shield_50k_mount_od = 308.000;
port_shield_50k_mount_bore = 300.000;
port_shield_4k_mount_od = 272.000;
port_shield_4k_mount_bore = 264.000;
port_shield_still_mount_od = 238.000;
port_shield_still_mount_bore = 232.000;
port_bridge_4k_shroud_od = 21.000;
port_bridge_4k_shroud_bore = 18.000;

module part_S6_2_02() {
  union() {
    // 50 K Al-6061 shield
    translate([0.000, 0.000, -5.500]) {
      difference() {
        cylinder(d=308.000, h=619.000, center=true);
        cylinder(d=300.000, h=621.000, center=true);
      }
    }
    // 4 K Au-OFHC shield
    translate([0.000, 0.000, -50.500]) {
      difference() {
        cylinder(d=272.000, h=469.000, center=true);
        cylinder(d=264.000, h=471.000, center=true);
      }
    }
    // Still 0.8 K Au-OFHC shield
    translate([0.000, 0.000, -95.500]) {
      difference() {
        cylinder(d=238.000, h=327.000, center=true);
        cylinder(d=232.000, h=329.000, center=true);
      }
    }
    // 4 K cryo-bridge shield tube
    translate([360.500, 0.000, -41.500]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=21.000, h=447.000, center=true);
        cylinder(d=18.000, h=449.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 535.000]) rotate([0.000, 0.000, 0.000]) part_S6_2_02();

part_S6_2_02();
