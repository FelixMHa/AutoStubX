

public class Benchmark5 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = input_1_0.toString();
        String output_2 = input_2_0.toString();

        
        // Compare output
        if (output_1.equals("-263074513") && output_2.equals("-225524834146")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

