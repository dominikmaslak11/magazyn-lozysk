package pl.lozyska.kiosk

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Podnosi mape po wlaczeniu tabletu.
 *
 * Gdy apka jest ustawiona jako ekran glowny, system i tak ja uruchomi i ten
 * odbiornik niczego nie zmienia. Zostaje jako zabezpieczenie na wypadek, gdyby
 * ekran glowny byl inny - wtedy to jedyna droga, zeby tablet po zaniku zasilania
 * wrocil do pokazywania mapy bez dotykania go.
 */
class StartPoWlaczeniu : BroadcastReceiver() {
    override fun onReceive(kontekst: Context, zamiar: Intent) {
        if (zamiar.action != Intent.ACTION_BOOT_COMPLETED) return
        val start = Intent(kontekst, MapaActivity::class.java)
        // Z odbiornika nie ma stosu zadan, wiec trzeba zalozyc nowy.
        start.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        kontekst.startActivity(start)
    }
}
