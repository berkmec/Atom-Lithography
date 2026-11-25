// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S6.8-01)
// ============================================================================
// part_id           : S6.8-01
// parent_bom_id     : S6.8
// subsystem         : S6
// part_name         : Seyreltme kriyostati ic-eklenti kulesi (MXC ~20 mK, Still, CP, isi esanjorleri)
// material          : OFHC Cu
// temp_stage        : 50K/4K/0.8K/100mK/20mK
// vacuum_grade      : Kriyo-vakum
// tolerance         : ±1 mK
// computed_mass_kg  : 27.17211
// envelope_mm       : 296.000 x 296.000 x 475.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 296.0000;
bbox_y = 296.0000;
bbox_z = 475.5000;

// Part-specific parametric dimensions
t_mxc_mk = 20.0;
p_cool_100mk_uw = 400.0;
n_stages = 5;
n_ag_hx = 3;

// Interface / port parameters (mm)
port_mxc_20mk_face_od = 190.000;
port_mxc_20mk_face_bore = 24.000;
port_pt420_50k_bore_od = 296.000;
port_pt420_50k_bore_bore = 92.000;
port_stage_4k_mount_od = 260.000;
port_stage_4k_mount_bore = 28.000;

module part_S6_8_01() {
  union() {
    // 50 K Al-6061 plate
    translate([0.000, 0.000, 127.000]) {
      difference() {
        cylinder(d=296.000, h=14.000, center=true);
        cylinder(d=92.000, h=16.000, center=true);
      }
    }
    // 4 K OFHC plate
    translate([0.000, 0.000, 8.000]) {
      difference() {
        cylinder(d=260.000, h=16.000, center=true);
        cylinder(d=28.000, h=18.000, center=true);
      }
    }
    // Still 0.8 K plate
    translate([0.000, 0.000, -110.000]) {
      difference() {
        cylinder(d=224.000, h=12.000, center=true);
        cylinder(d=28.000, h=14.000, center=true);
      }
    }
    // Cold Plate 100 mK
    translate([0.000, 0.000, -173.000]) {
      difference() {
        cylinder(d=204.000, h=10.000, center=true);
        cylinder(d=28.000, h=12.000, center=true);
      }
    }
    // MXC 20 mK plate
    translate([0.000, 0.000, -228.000]) {
      difference() {
        cylinder(d=190.000, h=16.000, center=true);
        cylinder(d=24.000, h=18.000, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([-650.000, 0.000, 720.000]) rotate([0.000, 0.000, 0.000]) part_S6_8_01();

part_S6_8_01();
