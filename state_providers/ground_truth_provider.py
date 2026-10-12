class GroundTruthStateProvider:
    ACTIVE_LANES = [1, 2]

    def __init__(self, engine):
        self.engine = engine

    def get_state(self):
        # "Kuyruk" = kavsakta GERCEKTEN bekleyen/bloke olmus arac sayisi
        # (vehicle.waitingDueToSignalQueue), henuz kavsaga hic yaklasmamis
        # (serbestce ilerleyen) araclar DAHIL DEGIL. Onceden burada
        # `crossed == 0` olan HER arac sayiliyordu -- yani spawn olup henuz
        # kesisimi gecmemis her sey, kavsaga 900px uzakta olsa bile. Bu,
        # kullanicinin GUI'de gozlemledigi bir soruna yol aciyordu: bir yon
        # spawn_interval geregi cok sayida arac biriktirdiginde (ör. uzun
        # sureli bir tikanikliktan dolayi), bu araclarin BUYUK COGUNLUGU
        # gorunur 900x900 alanin bile disinda (spawn noktasindan geriye
        # dogru yigilmis) olabiliyordu -- ama "queue_count" hepsini
        # sayiyordu, stratejiler de bu sayiyi index/cost hesaplarina
        # dogrudan sokuyordu. Sonuc: kavsaga hic yaklasmamis onlarca hayali
        # "talep", kavsakta GERCEKTEN bekleyen 1 araci bile ezebiliyordu.
        # `waitingDueToSignalQueue`, Vehicle.update_signal_wait_time()
        # tarafindan zaten dogru sekilde hesaplaniyor (kirmizida kendi
        # durma noktasinda bekleyen VEYA onundeki bekleyen araca zincirleme
        # bloke olan arac True olur; serbestce ilerleyen bir arac bu tick
        # hareket ettigi icin hemen False/eski haliyle kalir) -- sadece
        # panelin/state provider'in bunu hic okumamasi sorundu.
        state = {"right": 0, "down": 0, "left": 0, "up": 0}

        for direction in ["right", "down", "left", "up"]:
            count = 0

            for lane in self.ACTIVE_LANES:
                for vehicle in self.engine.vehicles[direction][lane]:
                    if vehicle.crossed == 0 and vehicle.waitingDueToSignalQueue:
                        count += 1

            state[direction] = count

        return state

    def get_rich_state(self):
        state = self.get_state()
        rich_state = {}

        for direction, queue_count in state.items():
            rich_state[direction] = {
                "queue_count": queue_count,
                "visible_count": None,
                "score": None,
                "queue_level": None,
                "is_saturated": False,
                "occupancy_ratio": None,
                "color": (230, 230, 230),
            }

        return rich_state