// ============================================================================
// Atom Lithography Machine — Parametric OpenSCAD Module (S5.6-01)
// ============================================================================
// part_id           : S5.6-01
// parent_bom_id     : S5.6
// subsystem         : S5
// part_name         : CF100 potasiz DC 28Si cubuk sublimasyon kaynagi, kriyo/su kalkani, pnomatik deklansor & PSU (Exp139, 11.8 kg)
// material          : 316LN
// temp_stage        : 300 K (UHV kaynak)
// vacuum_grade      : UHV 1.5e-10 Torr
// tolerance         : ±0.3 nm kalinlik
// computed_mass_kg  : 12.11494
// envelope_mm       : 170.000 x 176.000 x 279.500
// design_maturity   : M0_M1_DETAILED_CAD_DESIGN_ONLY
// no_lab_measurement: true
// iec61508_certified: false
// semi_s2_certified : false
// Units: millimeters (mm)
// ============================================================================

$fn = 64;

// Nominal bounding envelope parameters (mm)
bbox_x = 170.0000;
bbox_y = 176.0000;
bbox_z = 279.5000;

// Part-specific parametric dimensions
cf100_od = 152.0;
barrel_od = 136.0;
height_mm = 279.5;
growth_rate_nm_s = 0.1;

// Interface / port parameters (mm)
port_loadlock_cf100_base_od = 152.000;
port_loadlock_cf100_base_bore = 101.600;
port_loadlock_cf100_base_pcd = 130.200;
port_loadlock_cf100_base_bolts = 16;
port_qcm_neg_y_cf40_od = 69.500;
port_qcm_neg_y_cf40_bore = 38.000;
port_qcm_neg_y_cf40_pcd = 58.700;
port_qcm_neg_y_cf40_bolts = 6;
port_pbn_pos_y_cf40_od = 69.500;
port_pbn_pos_y_cf40_bore = 38.000;
port_pbn_pos_y_cf40_pcd = 58.700;
port_pbn_pos_y_cf40_bolts = 6;
port_mbe_tmp_pos_x_cf63_od = 113.500;
port_mbe_tmp_pos_x_cf63_bore = 63.500;
port_mbe_tmp_pos_x_cf63_pcd = 92.100;
port_mbe_tmp_pos_x_cf63_bolts = 8;

module part_S5_6_01() {
  union() {
    // Bottom CF100 flange mating Load-Lock +Z (Z=585.5 mm)
    translate([0.000, 0.000, 9.900]) rotate([180.000, 0.000, 0.000]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=101.600, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
    // 316LN MBE source barrel
    translate([0.000, 0.000, 114.900]) {
      difference() {
        cylinder(d=136.000, h=190.000, center=true);
        cylinder(d=126.000, h=192.000, center=true);
      }
    }
    // OFHC Cu water/LN2 cryoshroud
    translate([0.000, 0.000, 112.000]) {
      difference() {
        cylinder(d=102.000, h=174.000, center=true);
        cylinder(d=92.000, h=176.000, center=true);
      }
    }
    // -Y CF40 port for S5.6-02 QCM
    translate([0.000, -81.650, 119.500]) rotate([90.000, 0.000, 0.000]) {
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
    // +Y CF40 port for S5.6-03 PBN heater
    translate([0.000, 81.650, 89.500]) rotate([-90.000, 0.000, 0.000]) {
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
    // +X CF63 port for S5.6-04 80 L/s TMP+NEG
    translate([85.250, 0.000, 124.500]) rotate([0.000, 90.000, 0.000]) {
      difference() {
        cylinder(d=113.500, h=17.500, center=true);
        cylinder(d=63.500, h=19.500, center=true);
        translate([0, 0, 7.500]) cylinder(d=82.400, h=1.750);
        for (i = [0 : 8 - 1])
          rotate([0, 0, i * 360 / 8])
            translate([46.050, 0, 0])
              cylinder(d=8.400, h=19.500, center=true);
      }
    }
    // Top CF100 DC sublimation & pneumatic shutter flange
    translate([0.000, 0.000, 219.900]) {
      difference() {
        cylinder(d=152.000, h=19.800, center=true);
        cylinder(d=101.600, h=21.800, center=true);
        translate([0, 0, 8.650]) cylinder(d=120.500, h=1.750);
        for (i = [0 : 16 - 1])
          rotate([0, 0, i * 360 / 16])
            translate([65.100, 0, 0])
              cylinder(d=8.400, h=21.800, center=true);
      }
    }
  }
}

// World assembly mounting transform (global machine frame, mm / deg):
// translate([420.000, 0.000, 585.500]) rotate([0.000, 0.000, 0.000]) part_S5_6_01();

part_S5_6_01();
