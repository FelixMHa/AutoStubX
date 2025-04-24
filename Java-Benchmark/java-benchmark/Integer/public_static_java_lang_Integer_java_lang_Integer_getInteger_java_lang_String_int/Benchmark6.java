

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        String input_1_0 = String.valueOf(args[0]);
        Integer input_1_1 = Integer.valueOf(args[1]);
        String input_2_0 = String.valueOf(args[2]);
        Integer input_2_1 = Integer.valueOf(args[3]);


        // Perform computation         
        Integer output_1 = Integer.getInteger(input_1_0, input_1_1);
        Integer output_2 = Integer.getInteger(input_2_0, input_2_1);

        
        // Compare output
        if (output_1 == -2037711 && output_2 == 1809649) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

